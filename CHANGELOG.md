# CHANGELOG

すべての変更点は Keep a Changelog のフォーマットに準拠しています。  
遵守バージョン: 0.1.0

## [Unreleased]

---

## [0.1.0] - 2026-03-28

初期リリース。日本株自動売買システム「KabuSys」ライブラリのコア機能を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ初期化
  - kabusys パッケージの __version__ を "0.1.0" として公開。主要サブパッケージを __all__ でエクスポート（data, strategy, execution, monitoring）。

- 設定管理（kabusys.config）
  - .env/.env.local 自動読み込み機能（プロジェクトルートを .git または pyproject.toml から探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
  - .env パーサの実装（export 構文、クォート内のエスケープ、インラインコメントの扱い等に対応）。
  - 環境変数取得ユーティリティ（必須値の検証、デフォルト値の提供）。
  - 設定をカプセル化した Settings クラス（J-Quants / kabuステーション / Slack / DB パス / 環境・ログレベル判定ユーティリティを提供）。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を用いて、ターゲット日（前日 15:00 JST 〜 当日 08:30 JST）の記事を銘柄ごとに集約。
    - gpt-4o-mini を用いたバッチセンチメント評価（JSON Mode）。1チャンクあたり最大 20 銘柄。
    - 入力トリム (_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK) によるトークン肥大化対策。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフ再試行。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列、既知コードのみ採用、スコア数値化、±1.0 でクリップ）。
    - ai_scores テーブルへの冪等的書き込み（該当日のコードのみ DELETE → INSERT、部分失敗時に既存データを保護）。
    - テスト容易化のため OpenAI 呼び出し部分を差し替え可能に設計。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（225連動ETF）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次で ('bull' / 'neutral' / 'bear') を判定。
    - prices_daily からの ma200_ratio 計算、raw_news からマクロキーワード抽出、OpenAI（gpt-4o-mini）による macro_sentiment 評価を実装。
    - API エラーやパース失敗時のフェイルセーフ（macro_sentiment=0.0）。
    - 冪等的な market_regime への DB 書き込み（BEGIN / DELETE / INSERT / COMMIT + ROLLBACK 保護）。
    - 内部的に news ウィンドウ計算を news_nlp から利用（calc_news_window の利用）。

- データ基盤（kabusys.data）
  - ETL インターフェース（kabusys.data.etl）
    - pipeline.ETLResult を再エクスポート。

  - ETL パイプライン（kabusys.data.pipeline）
    - 差分更新・バックフィル・品質チェックを想定した ETLResult データクラスを追加（取得件数・保存件数・品質問題・エラー収集など）。
    - DuckDB を想定したユーティリティ (_table_exists, _get_max_date 等) を実装。
    - 市場カレンダー補助関数（内部）を実装して ETL の市場カレンダー処理をサポート。

  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー管理ロジックを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar テーブルが未取得の場合は曜日ベースでフォールバックする堅牢な設計。
    - database データ優先の一貫性ある判定ロジック（未登録日は曜日フォールバック）。
    - 夜間バッチ更新ジョブ（calendar_update_job）を実装。J-Quants クライアント経由で差分取得・バックフィル・健全性チェックを行い、結果を保存。

- リサーチ（kabusys.research）
  - Factor 計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER, ROE）等のファクター計算を実装。
    - DuckDB 上の SQL と Python を組み合わせた効率的実装。データ不足時は None を返すなど堅牢仕様。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）を実装。
    - IC（Information Coefficient、Spearman ρ）計算、ランク化ユーティリティ、ファクター統計サマリー（count/mean/std/min/max/median）を実装。
    - 外部依存を極力排した純 Python 実装（pandas 等に依存しない）。

### Design / Quality
- ルックアヘッドバイアス対策
  - すべての分析/スコアリング関数は内部で datetime.today() / date.today() を直接参照しない設計（target_date の引数による明示的指定）。
  - DB クエリは target_date 未満 / 未満を明示してルックアヘッドを防止。

- DB 書き込みの冪等性
  - ETL / AI 書き込み処理は既存レコードを保護する形で DELETE → INSERT または ON CONFLICT 相当の動作を意識した実装。

- OpenAI API 周りの堅牢性
  - JSON Mode の結果を厳密に検証し、パース失敗や部分エラーに対してはフォールバック動作（スキップまたは中立値）を採用。
  - リトライ・バックオフの一貫した実装。

### Notes
- OpenAI（gpt-4o-mini）API キーは関数引数で注入可能。指定がない場合は環境変数 OPENAI_API_KEY を参照。
- DuckDB を前提とした SQL 実装のため、DuckDB バージョン依存の扱い（executemany の空リスト制約など）に配慮した実装が含まれます。
- 一部のユーティリティ（jquants_client 等）は外部モジュールに依存するインターフェースとして想定（実装は別モジュール）。

### Breaking Changes
- 初期リリースのため該当なし。

### Fixed
- 初期リリースのため該当なし。

### Security
- 初期リリースのため該当なし。

---

開発・運用上の注記や追加の既知の制約・TODO はリポジトリ内の各モジュールの docstring を参照してください。