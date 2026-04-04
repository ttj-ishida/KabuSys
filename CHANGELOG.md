# Changelog

すべての重要な変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠し、セマンティック バージョニングを採用します。
（https://keepachangelog.com/ja/1.0.0/）

※この CHANGELOG は与えられたコードベースから推測して作成しています。

## [Unreleased]

### Added
- （今後の作業予定をここに記載）

---

## [0.1.0] - 2026-04-04

初版リリース。パッケージ全体の核となる機能群を実装。

### Added
- パッケージ公開
  - kabusys パッケージを公開。サブモジュールとして data, research, ai, monitoring, execution, strategy 等を想定してエクスポート。

- 環境設定 / 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動読み込み機能を実装。
    - プロジェクトルートの自動検出（.git または pyproject.toml を起点）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
    - OS 環境変数を保護する protected オプションを採用（.env による上書きを制御）。
  - .env ファイルパーサを実装。以下をサポート／考慮：
    - 空行・コメント行（#）のスキップ。
    - export KEY=val 形式のサポート。
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理。
    - クォート無しの行での行内コメント認識（直前がスペース/タブの場合のみ）。
  - Settings クラスを実装し、アプリケーション設定値をプロパティ経由で取得可能に：
    - J-Quants / kabuステーション / LINE API / DB パス / 監視閾値 / 環境（development/paper_trading/live） / ログレベル等を提供。
    - 必須環境変数未設定時は ValueError を発生させる _require ユーティリティを実装。
    - env / log_level の入力検証（許容値外は ValueError）。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）を用いてセンチメントを取得する score_news を実装。
    - タイムウィンドウ計算（JST 前日 15:00 ～ 当日 08:30 に対応、UTC に変換）。
    - 1銘柄あたり最大記事数・最大文字数でトリムし、最大バッチ数（20銘柄）で API に送信。
    - 再試行（429・ネットワーク断・タイムアウト・5xx）を指数バックオフで実装。
    - レスポンスのバリデーション（JSON 抽出、results 配列、code・score の検証、数値チェック）。
    - スコアは ±1.0 にクリップ。フェイルセーフにより個別チャンク失敗時も他銘柄の処理を継続。
    - 取得したスコアは ai_scores テーブルへ冪等（DELETE → INSERT）で書き込む実装。
    - テスト容易性のため OpenAI 呼び出し部を差し替え可能（ユニットテストでの patch を想定）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（Nikkei 225 連動型）の 200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - ma200_ratio の計算（ターゲット日未満のデータのみ使用してルックアヘッドバイアスを防止）。
    - マクロキーワードによる raw_news のフィルタリング（最大件数制限）。
    - OpenAI 呼び出し（gpt-4o-mini, JSON mode）。API 失敗時は macro_sentiment=0.0 にフォールバック。
    - 重み付け合成・クリップ・閾値判定によるラベル付け。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - API キーは引数または環境変数 OPENAI_API_KEY で指定。未設定時は ValueError。

- リサーチ（kabusys.research）
  - factor_research モジュールに以下を実装：
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（データ不足時は None）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率など。
    - calc_value: raw_financials から最新の財務データを取得して PER / ROE を計算（EPS 0/欠損は None）。
    - DuckDB のウィンドウ関数を活用した高効率 SQL 実装。
  - feature_exploration モジュールに以下を実装：
    - calc_forward_returns: 指定ホライズンの将来リターンを一括取得（デフォルト [1,5,21]）。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。データ不足時は None。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を算出。
    - rank: 同順位は平均ランクを返すランク付けユーティリティ（丸め処理による tie 対応）。
    - 外部ライブラリに依存せず標準ライブラリ + DuckDB で実装。

- データカレンダー管理（kabusys.data.calendar_management）
  - market_calendar テーブルを使った営業日判定・探索機能を実装：
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - DB にデータがない場合は曜日ベースでフォールバック。
    - 最大探索日数制限 (_MAX_SEARCH_DAYS) により無限ループを防止。
    - calendar_update_job により J-Quants API から差分取得 → 保存（バックフィル・健全性チェック付き）を実装。
    - DB 登録値優先、未登録日は曜日フォールバックという一貫した振る舞いを設計。

- ETL / パイプライン（kabusys.data.pipeline / kabusys.data.etl）
  - ETLResult dataclass を実装し、ETL 実行結果（取得数・保存数・品質問題・エラー）を集約して出力可能に。
  - pipeline モジュールの基本ユーティリティ（差分取得、保存、品質チェックの呼び出し方を想定）用の基盤関数を実装（テーブル存在チェック、最大日付取得等）。
  - kabusys.data.etl で ETLResult を再エクスポート。

### Changed
- （初版のため過去変更は無し）

### Fixed
- （初版のため過去修正は無し）

### Security
- OpenAI API キーが未設定の場合は明示的に ValueError を発生させることで、誤動作を防止。

### Notes / Design decisions
- ルックアヘッドバイアス防止:
  - 各種処理（news window / ma200 / feature 計算 / forward returns / regime scoring）はすべて target_date を明示的に受け取り、datetime.today()/date.today() を内部参照しない設計。
- フェイルセーフ:
  - 外部 API 呼び出し失敗（OpenAI, J-Quants 等）は例外直結ではなく、可能な限りフォールバック（スコア 0.0 やスキップ）して全体処理を継続する方針。
- DuckDB 前提:
  - 内部データストアは DuckDB を前提とした SQL 実装になっている（window 関数・executemany の挙動を考慮）。
- テスト容易性:
  - OpenAI 呼び出し部はモジュール単位で差し替え可能に設計（unit test での patch を想定）。

### Breaking Changes
- なし（初版）

---

今後のリリースでは以下の改善が想定されます（例）:
- CLI や cron ジョブ用のエントリポイント実装
- モデル・プロンプトチューニング、より厳密なレスポンス検証
- 追加の監視・アラート機能（LINE 通知等）
- ETL の並列化・パフォーマンス改善

（以上）