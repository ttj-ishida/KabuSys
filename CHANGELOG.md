# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。  
このファイルはコードベース（kabusys）から推測できる機能追加・設計方針・互換性注意点に基づき作成しています。

※ 生成日: 2026-03-31

## [Unreleased]

### Added
- 採用予定の機能や開発中の改善点をここに記載してください。

---

## [0.1.0] - 2026-03-31

最初の公開リリース（初期実装）。主にデータ基盤、リサーチユーティリティ、AIベースのニュース・レジーム判定、および環境設定管理のコア機能を実装。

### Added
- パッケージ初期化
  - kabusys パッケージの __version__ を "0.1.0" に設定し、主要サブパッケージ（data, strategy, execution, monitoring）をエクスポート。

- 環境変数 / 設定管理（kabusys.config）
  - .env/.env.local の自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - .env パーサーを実装（コメント、export プレフィックス、シングル／ダブルクォート内のエスケープを処理）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 環境変数保護（OS 環境変数を protected set として上書き防止）機構を実装。
  - Settings クラスを導入し、主要設定をプロパティとして提供（J-Quants / kabu API / Slack / DB パス / 監視閾値 / 環境区分 / ログレベル等）。
  - 必須キー取得時に未設定なら ValueError を送出する _require を提供。
  - 有効な環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL）。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント（ai_score）を算出。
    - バッチ処理（最大 20 銘柄/チャンク）、1銘柄あたりの記事数・文字数制限、JSON Mode の応答バリデーションを実装。
    - レート制限・ネットワーク障害・5xx に対するエクスポネンシャルバックオフとリトライ。
    - レスポンスの堅牢なパースとスコアクリップ（±1.0）。部分成功時に既存スコアを保護するための個別 DELETE → INSERT ロジックを採用（DuckDB 互換性配慮）。
    - 時間ウィンドウ計算（JST に基づく前日 15:00 ～ 当日 08:30 相当）を提供する calc_news_window。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225 連動）200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定・保存。
    - prices_daily / raw_news を参照し、DuckDB 経由で ma200_ratio を計算、マクロニュースはキーワードベースで抽出。
    - OpenAI 呼び出しは独立実装でリトライ・例外ハンドリングを備える（フェイルセーフとして API 失敗時は macro_sentiment=0.0）。
    - 判定結果は market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。

- データプラットフォーム（kabusys.data）
  - ETL パイプライン基盤（kabusys.data.pipeline）
    - ETLResult データクラスを導入し、ETL 実行結果（取得数／保存数／品質問題／エラー）を構造化して返却。
    - ETL の差分更新・バックフィル・品質チェック設計を注記（実装済のユーティリティ関数・定数を含む）。
  - ETL 公開インターフェース（kabusys.data.etl）で ETLResult を再エクスポート。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを基に営業日判定ロジックを実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した挙動を採用。
    - calendar_update_job を実装し J-Quants API から差分取得して市場カレンダーを冪等に更新（バックフィル・健全性チェックあり）。
    - DuckDB からの日付変換ユーティリティやテーブル存在確認ユーティリティを提供。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research モジュールに以下を実装:
    - calc_momentum: 1M/3M/6M リターンと ma200 乖離を計算（データ不足時は None）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を取得し PER/ROE を計算（PBR/配当利回りは未実装）。
  - feature_exploration モジュールに以下を実装:
    - calc_forward_returns: 任意ホライズンの将来リターン（デフォルト: 1,5,21 営業日）。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算。
    - rank: 同順位は平均ランクで扱うランク変換ユーティリティ（丸め処理で ties 検出を安定化）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）の計算。

### Fixed
- DuckDB 周りの互換性配慮
  - executemany に空リストを渡せない DuckDB 0.10 の挙動を考慮し、空パラメータを渡さないガードを追加。
  - テーブル存在確認や日付型の取り扱いをユーティリティ化して堅牢性を向上。

### Security
- 環境変数の取り扱い改善
  - .env 読み込み時に OS の既存環境変数を保護する protected set を導入し、意図しない上書きを防止。
  - 必須トークン（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN など）は未設定時に明確な例外を発生させることでミスを早期検出。

### Notes / Migration
- 必須環境変数
  - 本リリースで利用される主要な環境変数:
    - OPENAI_API_KEY（OpenAI 呼び出し）
    - JQUANTS_REFRESH_TOKEN（J-Quants API）
    - KABU_API_PASSWORD / KABU_API_BASE_URL（kabuステーション API）
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（通知用 Slack）
  - .env.example を参考に .env/.env.local を用意してください。自動ロードはプロジェクトルート（.git または pyproject.toml 参照）から行われます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- デフォルト DB パス
  - DuckDB: data/kabusys.duckdb（環境変数 DUCKDB_PATH で変更可能）
  - SQLite（監視用）: data/monitoring.db（環境変数 SQLITE_PATH で変更可能）

- OpenAI 呼び出し
  - gpt-4o-mini を使用、JSON Mode（response_format={"type": "json_object"}）で厳密な JSON を期待する設計。
  - テスト容易性のため内部の _call_openai_api はモック差し替えが想定されている（unittest.mock.patch の利用を想定）。

- レジーム判定 / ニュース解析
  - ルックアヘッドバイアス防止のため、本実装は内部で datetime.today() / date.today() を参照せず、明示的な target_date パラメータで処理を行う設計。
  - API 失敗時はフェイルセーフで「中立」や「スコア算出スキップ（0相当）」へフォールバックする挙動。

### Removed
- なし（初回リリース）

---

開発者・利用者向けの補足やバグ報告・機能要望はリポジトリの Issue にお願いします。