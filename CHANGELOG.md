# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、Semantic Versioning を使用します。

※リリース日や著者情報はコードベースから確定的に取得できないため、実装内容の要約に基づいて記載しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-29

初期リリース。日本株自動売買プラットフォームのコアライブラリを提供します。主な追加機能・モジュールは以下の通りです。

### Added
- パッケージ基礎
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。パッケージのエクスポートモジュールを `__all__ = ["data", "strategy", "execution", "monitoring"]` で定義（src/kabusys/__init__.py）。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルと環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み優先順: OS 環境変数 > .env.local > .env
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - プロジェクトルートは `.git` または `pyproject.toml` を手がかりに探索（CWD に依存しない）。
  - .env パース処理を強化（コメント行、export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取り扱いなど）。
  - 環境変数必須チェック関数 `_require` を提供。
  - `Settings` クラスを提供し、アプリ設定（J-Quants トークン、kabu API パスワード/ベース URL、Slack トークン/チャンネル、DB パス、環境種別、ログレベル判定、is_live/is_paper/is_dev）をプロパティで取得できるようにした。
  - `KABUSYS_ENV` と `LOG_LEVEL` のバリデーション（許容値セット）を実装。

- AI 関連（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols テーブルから銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄別センチメント（-1.0〜1.0）を計算。
    - バッチ処理（最大20銘柄／チャンク）、記事数・文字数上限、レスポンスバリデーション、スコアの ±1.0 クリップ、部分成功時の DB 書き換え戦略（対象コードのみ DELETE → INSERT）を実装。
    - リトライ戦略（429、ネットワーク断、タイムアウト、5xx を対象に指数バックオフ）とフェイルセーフ（API 失敗時はスキップして処理継続）。
    - 時刻ウィンドウ計算（JST 基準の前日 15:00 ～ 当日 08:30 相当）を提供する `calc_news_window`。
    - テスト容易性のため、OpenAI 呼び出し部分はモジュール内でラップし差し替え可能に実装。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を組み合わせて日次の市場レジーム（bull / neutral / bear）を判定。
    - prices_daily / raw_news からのデータ取得、OpenAI 呼び出し、スコア合成、market_regime テーブルへの冪等書き込みを実装。
    - API のリトライ・バックオフ、API 失敗時の macro_sentiment=0.0 フォールバック、ルックアヘッドバイアス対策（target_date 未満のみ参照）などの設計方針を採用。
  - AI モジュールのエクスポート（src/kabusys/ai/__init__.py）に `score_news`（news_nlp）を公開。

- データ基盤（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダー（market_calendar テーブル）の管理と夜間バッチ更新ジョブ `calendar_update_job` を実装。J-Quants クライアント経由で差分取得 → 保存を行う。
    - 営業日判定ヘルパー: `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day` を提供。DB にデータがない場合は曜日ベースのフォールバックを使用。
    - 最大探索日数やバックフィル、健全性チェックなどの保護ロジックを実装。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETL 実行結果を表す `ETLResult` dataclass を追加（取得数、保存数、品質チェック結果、エラーリスト等を保持）。
    - DuckDB を用いた差分取得、最終日取得ヘルパー、テーブル存在チェックなどのユーティリティを実装。
    - jquants_client と quality モジュール（インターフェース使用）を組み合わせる設計。
  - `src/kabusys/data/__init__.py` はデータパッケージのエントリポイント（現状空の placeholder）。

- リサーチ / ファクター分析（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR）、Value（PER、ROE）等を DuckDB + SQL で実装。prices_daily / raw_financials のみ参照し、外部 API にはアクセスしない。
    - データ不足時の None 返却、営業日スキャンバッファ等の配慮。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic: Spearman の ρ）、ランク関数（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリと DuckDB のみで実装。
  - research パッケージのエクスポート（src/kabusys/research/__init__.py）で主要関数群を公開。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- 環境変数や API キーの取扱いに関しては直接ログ出力しない等の配慮がコードから読み取れますが、秘密情報の取り扱いは運用ルールに従ってください（OpenAI / Slack / KABU API キーは環境変数で管理）。

### Notes / 設計方針のハイライト
- ルックアヘッドバイアス防止のため、日付参照は全て関数引数の target_date ベースで行い、datetime.today()/date.today() の直接参照を避ける方針を採用（AI スコア／レジーム判定／ファクター計算等）。
- DB 書き込みは冪等性を意識（DELETE → INSERT や ON CONFLICT パターン、部分書換で部分失敗の被害を低減）。
- OpenAI API 呼び出し部分はラッパー関数で分離し、テスト時に差し替え可能に実装（unittest.mock.patch でモック化しやすい）。
- 外部依存（pandas 等）は最小化し、DuckDB の SQL を活用する設計。

---

今後のリリース候補（例）
- Unreleased: エラーハンドリング強化、詳細なログ出力フォーマット、追加のファクター・特徴量、ETL の並列化、モニタリング/アラート機能の追加など。