# Changelog

すべての変更は Keep a Changelog の形式に従い、日本語で記載しています。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-03-29
初回リリース。日本株自動売買システムのコアライブラリを公開します。主な追加点は以下の通りです。

### 追加（Added）
- パッケージ基盤
  - パッケージ初期化とバージョン情報を追加（src/kabusys/__init__.py, __version__ = "0.1.0"）。
  - モジュール公開 API を __all__ に定義（data, strategy, execution, monitoring）。

- 環境設定（src/kabusys/config.py）
  - .env/.env.local からの自動環境変数ロード機能を実装。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - プロジェクトルート検出は .git または pyproject.toml を基準に行い、CWD に依存しない実装。
    - .env の読み込み順序: OS 環境変数 > .env.local > .env（.env.local は上書き）。
    - OS 環境変数を保護する protected セットの導入により、既存の OS 環境変数を誤って上書きしない。
  - .env パーサ実装（クォート、エスケープ、コメントの扱いをサポート）。
  - 必須環境変数取得ヘルパ _require と Settings クラスを提供。
    - J-Quants / kabuステーション / Slack / DB パス / 環境種別（development/paper_trading/live）などのプロパティを定義。
    - LOG_LEVEL や KABUSYS_ENV の値検証を実装。
    - duckdb/sqlite パスのデフォルト値を設定。

- AI（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode でバッチ評価して ai_scores テーブルへ書き込む処理を実装。
    - 処理フロー: 時間ウィンドウ算出（calc_news_window）、記事抽出、銘柄チャンク化（最大 20 銘柄/チャンク）、API リトライ（429/ネットワーク/5xx に対して指数バックオフ）、レスポンス検証（results リストのバリデーション）、スコアの ±1.0 クリップ、部分失敗を考慮した安全な DB 書き込み（DELETE → INSERT）。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能に設計（_call_openai_api を patch でモック可能）。
    - ニュースウィンドウ（JST ベース）を calc_news_window で提供（前日 15:00 JST 〜 当日 08:30 JST 相当の UTC 範囲）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出・保存する機能を実装。
    - マクロ記事抽出のためのキーワードリストと OpenAI 呼び出し（gpt-4o-mini）を組み合わせ、冪等に market_regime テーブルへ書き込みを行う（BEGIN / DELETE / INSERT / COMMIT）。
    - API 失敗時はフェイルセーフとして macro_sentiment = 0.0 を使用する設計。
    - OpenAI 呼び出しのリトライ・エラーハンドリング（RateLimit / 接続 / タイムアウト / 5xx）を実装。
    - ルックアヘッドバイアス回避設計（datetime.today() を直接参照しない、DB クエリで date < target_date を利用）。

- データ基盤（src/kabusys/data）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを用いた営業日判定 / next/prev_trading_day / get_trading_days / is_sq_day 等のユーティリティを実装。
    - DB 未取得時の曜日ベースのフォールバック、最大探索日数制限 (_MAX_SEARCH_DAYS)、JPX カレンダーの夜間差分更新ジョブ calendar_update_job を実装（J-Quants クライアント経由で取得 → 保存）。
    - バックフィルや健全性チェック（過度の将来日付の検出）を実装。
  - ETL パイプライン関連（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを公開（取得件数、保存件数、品質チェック結果、エラー情報等を保持）。
    - ETL の差分取得、バックフィル、品質チェック方針を実装するためのユーティリティ関数群の骨格を実装（_get_max_date など）。
    - jquants_client 経由での idempotent 保存（ON CONFLICT 相当）を想定した設計。

- リサーチ（src/kabusys/research）
  - factor_research（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER、ROE）、Volatility（20 日 ATR）および流動性（20 日平均売買代金、出来高変化率）を DuckDB 上で計算する関数を実装。
    - データ不足時の扱い（None を返す）やスキャン範囲バッファを考慮した設計。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）やランク付けユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - スピアマン順位相関（IC）の計算や欠損/非有限値除外、最小サンプル数チェック等を実装。
  - パッケージ公開（src/kabusys/research/__init__.py）で主要関数を再エクスポート。

### 変更（Changed）
- なし（初版のため）。

### 修正（Fixed）
- なし（初版のため）。

### 注意事項 / 設計上の決定
- ルックアヘッドバイアス防止:
  - AI スコアリングおよびリサーチ機能は内部で datetime.today()/date.today() を直接参照しないよう設計されています。必ず target_date を引数に渡して処理を行います。
- フェイルセーフ設計:
  - OpenAI API の失敗時は例外を上位に伝播させず（スコアリング失敗時は該当コードをスキップする等）、システム全体の継続を優先します（ただし、API キー未設定時は ValueError を送出）。
- テスト性:
  - OpenAI 呼び出しポイントはモック可能（_call_openai_api を patch）にしてあり、ユニットテストで API 実際呼び出しを防げます。
- データベース:
  - DuckDB を主要な分析 DB として前提（関数シグネチャは DuckDB 接続を受け取る）。SQL は互換性を考慮して記述されています。
- .env パース:
  - シェル形式の .env を柔軟に解釈（export プレフィックス、クォート、バックスラッシュエスケープ、行内コメントの一部扱い等）します。

### 将来的な作業（TODO / 今後の予定）
- strategy / execution / monitoring の実装（パッケージ API には含まれているが本版では内部実装の追加が必要）。
- jquants_client の実装詳細（本リリースでは呼び出し箇所を想定したコードを含む）。
- CLI / ワークフロー（スケジューラ）やモニタリング（Slack 通知等）の統合。
- より詳細な品質チェックルール実装と ETL の自動化テスト整備。

---

作成した内容はコードベースのコメントと関数説明から推測してまとめたものです。必要であれば、実際の変更日や追加のチケット / PR 番号、あるいはさらに詳細なセクション（Deprecated / Security / Migration）を追記します。