# Keep a Changelog — CHANGELOG

すべての重要な変更をこのファイルで記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

変更履歴のバージョンは semver に従います。

## [Unreleased]

- 開発中の変更や未リリースの作業はここに記載します。

---

## [0.1.0] - 2026-03-28

初回リリース

### Added
- パッケージ初期化
  - `kabusys.__init__` によりパッケージ名とバージョン（0.1.0）を公開。
  - パブリックモジュールとして data / research / ai / 等をエクスポート。

- 設定 / 環境変数管理
  - `kabusys.config` を追加。
  - .env ファイル（プロジェクトルートの `.env` / `.env.local`）を自動で読み込む機能を実装（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
  - プロジェクトルートの検出は `pyproject.toml` または `.git` を起点に親ディレクトリを探索して行う（CWD に依存しない実装）。
  - .env パーサを実装（コメント・export 形式・クォート・エスケープに対応）。
  - `Settings` クラスを提供し、J-Quants / kabu ステーション / Slack / DB パス / システム設定等のプロパティを環境変数から取得。
  - 必須変数取得時に未設定なら `ValueError` を投げる `_require` を用意。
  - `KABUSYS_ENV` と `LOG_LEVEL` の値検証を実装（許可値のチェック）。

- AI 関連（ニュース NLP / レジーム判定）
  - `kabusys.ai.news_nlp`
    - raw_news と news_symbols を集約して銘柄ごとのニューステキストを作成。
    - OpenAI（gpt-4o-mini）の JSON mode を使いバッチでセンチメント（-1〜1）を取得。
    - バッチング（最大20銘柄）、1銘柄あたり記事数・文字数制限の実装。
    - 再試行（429・ネットワーク断・タイムアウト・5xx）を指数バックオフで実装。
    - レスポンス検証処理を実装（JSON パース、results の構造、既知コードのチェック、数値チェック、スコアの ±1 クリップ）。
    - 書き込みは idempotent に ai_scores テーブルへ（DELETE → INSERT、部分失敗で他のコードを保護）。
    - テストのために `_call_openai_api` を patch 可能にしている。
    - `calc_news_window`（ニュース収集ウィンドウ計算）を実装（JST ベースの時間ウィンドウを UTC に変換）。

  - `kabusys.ai.regime_detector`
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を組み合わせて日次市場レジーム（bull/neutral/bear）を判定。
    - LLM 呼び出しは gpt-4o-mini、API エラー時はフェイルセーフで macro_sentiment=0.0 を採用。
    - DuckDB からのデータ取得時にルックアヘッドバイアスを防ぐ設計（target_date 未満のデータのみ使用、datetime.today() を参照しない）。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - LLM 呼び出し用の `_call_openai_api` を別実装にしてモジュール結合を避け、テスト時は差し替え可能。

- リサーチ（ファクター計算・特徴量探索）
  - `kabusys.research.factor_research`
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算する `calc_momentum` を実装。データ不足時の挙動（None）を定義。
    - Volatility & Liquidity: 20 日 ATR、ATR 比、20 日平均売買代金、出来高比を計算する `calc_volatility` を実装。true_range の NULL 伝播の扱いに配慮。
    - Value: raw_financials から直近財務データを取得して PER/ROE を計算する `calc_value` を実装（EPS が 0 または NULL の場合は None）。
    - 全関数とも DuckDB と prices_daily / raw_financials を参照し、本番発注 API へはアクセスしない設計。

  - `kabusys.research.feature_exploration`
    - 将来リターン計算 `calc_forward_returns`（任意の horizon、デフォルト [1,5,21]）。
    - IC（Spearman の ρ）を計算する `calc_ic`（コード結合、None 値除外、3 銘柄未満で None）。
    - ランキング関数 `rank`（同順位は平均ランク、丸めによる ties 対応）。
    - ファクター統計サマリー `factor_summary`（count/mean/std/min/max/median）。

  - `kabusys.research.__init__` に主要関数を再エクスポート。

- データプラットフォーム / ETL / カレンダー
  - `kabusys.data.calendar_management`
    - JPX カレンダー管理（market_calendar テーブル）および営業日判定用ユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB 登録値を優先し、未登録日は曜日ベースのフォールバックを行う一貫した挙動。
    - calendar_update_job を追加（J-Quants API から差分取得し保存、バックフィル/健全性チェックを実装）。
    - 最大探索日数やバックフィル日数等を定数化し安全策を導入。

  - `kabusys.data.pipeline`（ETL パイプライン）
    - ETL の設計に基づくユーティリティ関数（差分取得、保存、品質チェック連携）と内部ユーティリティを実装。
    - ETL 実行結果を表す `ETLResult` dataclass を追加（品質問題・エラー情報を含む、辞書化機能あり）。
    - `_get_max_date` 等の DB ユーティリティを実装。
    - `kabusys.data.etl` で `ETLResult` を再エクスポート。

  - `kabusys.data.calendar_management` と `pipeline` は jquants_client と quality モジュールへ依存（外部 API クライアント / 品質チェック連携を想定）。

- 汎用設計/運用上の配慮
  - DuckDB を主要なオンディスク分析 DB として採用し、SQL を中心に処理（パフォーマンス配慮）。
  - ルックアヘッドバイアス防止方針を各種 AI / 研究モジュールで徹底（datetime.today / date.today を内部で参照しない）。
  - OpenAI 呼び出しに対して堅牢なリトライ/バックオフ、レスポンス検証、フェイルセーフを実装。
  - テスト容易化のため外部呼び出しポイント（OpenAI API 呼び出しなど）を patch 可能に実装。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- OpenAI API キー等の機密は環境変数経由で取得する設計。`.env` の自動ロードは任意で無効化可能（`KABUSYS_DISABLE_AUTO_ENV_LOAD`）。

---

注記 / 既知の動作・制約
- OpenAI API の使用には `OPENAI_API_KEY`（関数呼び出し引数で注入可）が必須。未指定の場合は ValueError を送出する実装が多く含まれる。
- 必須環境変数（例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`）は `Settings` 経由で取得され、未設定時は明示的な例外メッセージが出力される。
- DuckDB executemany に関する互換性を考慮して、空リストでの executemany を避けるガードが入っている（DuckDB 0.10 対応）。
- news_nlp / regime_detector の AI 呼び出しは gpt-4o-mini を想定してプロンプト・JSON mode に依存した処理を行っている。OpenAI SDK の将来変更に備え、status_code の有無を安全に扱う処理を入れている。
- calendar_update_job 等は外部 API（J-Quants）への依存があるため、ネットワーク・API エラー時はログ出力のうえ 0 を返しフェイルセーフな振る舞いをする。

---

開発者向け
- テスト時は各モジュール内の `_call_openai_api` をモックして API 呼び出しをエミュレート可能。
- .env 自動ロードはプロジェクトルート検出を行うため、パッケージ配布後も相対パスの問題を避ける設計。

（以上）