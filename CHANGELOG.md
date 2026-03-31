# Changelog

すべての注記は Keep a Changelog の仕様に準拠し、セマンティックバージョニングの慣習に従います。

- リポジトリ初期バージョン: 0.1.0
- リリース日: 2026-03-31

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-31
初回リリース。日本株自動売買／リサーチプラットフォームのコア機能を実装しました。

### Added
- パッケージ基盤
  - パッケージ名: `kabusys`、バージョン `0.1.0` を定義（src/kabusys/__init__.py）。
  - 公開モジュール群: data, strategy, execution, monitoring をエクスポート。

- 設定管理
  - 環境変数読み込み・管理モジュールを追加（src/kabusys/config.py）。
    - プロジェクトルート（.git / pyproject.toml）を起点に自動で .env, .env.local を読み込む自動ロード機能を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - .env 拡張パーサを実装（export 指定、シングル/ダブルクォート、エスケープ、インラインコメントの扱いなどに対応）。
    - OS 環境変数を保護する protected 上書き制御（.env.local は既存 OS 変数を上書きしない）。
    - 必須キー取得ヘルパー `_require` と Settings クラスを提供。J-Quants / kabu API / Slack / DB パス / 監視閾値 / 環境（development/paper_trading/live）/ログレベルの検証付きプロパティを用意。

- AI（ニュースNLP・レジーム検出）
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信してスコアリング。
    - バッチ処理・チャンクサイズ、1銘柄あたりの最大記事数/文字数トリム、最大再試行（指数バックオフ）などを実装。
    - レスポンスバリデーション（JSON 抽出、results 配列、code/score の検証、スコアを ±1.0 にクリップ）。
    - 書き込みは部分置換（取得できたコードのみ DELETE → INSERT）で部分失敗時のデータ保全を考慮。
    - テスト容易性のため、OpenAI 呼び出し部分は内部関数を patch して差し替え可能。
    - 公開関数: score_news(conn, target_date, api_key=None) → 書き込み銘柄数を返却。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動）の 200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジームを判定（bull/neutral/bear）。
    - OpenAI（gpt-4o-mini）呼び出し、JSON パース、リトライ/バックオフ、API 失敗時のフェイルセーフ（macro_sentiment=0.0）を実装。
    - DuckDB を用いたデータ読み込み（prices_daily / raw_news）と market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - 公開関数: score_regime(conn, target_date, api_key=None) → 成功時 1 を返却。

- データプラットフォーム（Data）
  - ETL 用インターフェースと結果型（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult dataclass を提供（取得件数・保存件数・品質チェック問題・エラー一覧・to_dict メソッド等）。
    - 差分更新・バックフィル・品質チェックに対応するパイプライン設計を意図（実装の一部を含む）。
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを使った営業日判定 API を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録がない場合は曜日ベース（週末除外）でフォールバックするロジックを追加。
    - データ先読み・バックフィル・健全性チェック・J-Quants からの差分取得を行う夜間更新ジョブ calendar_update_job を実装。
    - JPX カレンダーの idempotent な保存（ON CONFLICT/上書き想定）に対応する設計。

- リサーチ（Research）
  - ファクタ計算・特徴量探索モジュールを追加（src/kabusys/research/*）。
    - calc_momentum: 1M/3M/6M リターン・200 日 MA 乖離を計算。
    - calc_volatility: 20 日 ATR（平均 true range）、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から PER/ROE を計算（target_date 以前の最新財務データを使用）。
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得。
    - calc_ic: factor と将来リターンのスピアマンランク相関（IC）を計算（レコード不足時は None）。
    - rank: 平均ランク（同順位は平均ランク）を計算。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを算出。
  - それぞれ DuckDB の prices_daily / raw_financials に依存し、外部 API 呼び出しは行わない設計。

- モジュール公開整理
  - ai パッケージは score_news をエクスポート。
  - research パッケージは主要関数群（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）をエクスポート。
  - data.etl は ETLResult を再エクスポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは明示的に引数で注入可能（api_key）か、環境変数 OPENAI_API_KEY を参照する設計。未設定時は ValueError を送出して誤った無認可呼び出しを防止。
- .env 自動ロード時に OS の既存環境変数を保護する仕組みを導入（.env.local の override 制御含む）。

### Notes / Implementation details / 設計上の配慮
- ルックアヘッドバイアス回避: 全てのモジュールで datetime.today()/date.today() を直接参照せず、外部から与えた target_date を基準に計算する方針を採用。
- OpenAI 呼び出し部はテスト容易性を考慮し内部関数で分離（unittest.mock.patch による差し替えが可能）。
- API 呼び出しは RateLimit / ネットワーク断 / Timeout / 5xx をリトライ対象とし、指数バックオフを行う。致命的な API エラーやレスポンスパース失敗はフェイルセーフでスコアを neutral（0.0）扱いにするなど継続性を重視。
- DuckDB をデータ層に採用。各処理で BEGIN/DELETE/INSERT/COMMIT (および例外時の ROLLBACK) による冪等書き込みを行うことで別プロセスからの再実行に耐える設計。
- リサーチ用ユーティリティは pandas 等に依存せず標準ライブラリおよび DuckDB SQL で実装。これにより軽量かつ移植性を高めている。

### Deprecated
- （該当なし）

### Removed
- （該当なし）

---

将来的なリリースでは、以下のような項目が想定されます（未実装・改善候補）:
- Strategy / execution / monitoring モジュールの実装詳細（現状は公開のみ）。
- J-Quants クライアントおよび kabu API クライアントの具体的な実装・統合テスト。
- CI/CD 用の自動テスト・モックデータセット、さらに詳細な品質チェックルールやアラート機能の拡充。
- OpenAI 呼び出しのコスト削減のためのキャッシュや軽量モデル切替機構。

必要であれば、この CHANGELOG を英語化したり、各ファイルごとのより詳細な変更理由（why）や、将来の互換性に関する注記を追加します。