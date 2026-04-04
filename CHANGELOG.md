# Changelog

すべての変更は Keep a Changelog のガイドラインに従って記載しています。  
このプロジェクトのバージョニングは SemVer に従います。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-04
初回公開リリース。日本株自動売買プラットフォームのコアライブラリを実装しました。以下は主な追加機能と設計上の注意点です。

### Added
- パッケージ全体
  - 初期バージョンとして kabusys v0.1.0 を公開。

- 環境設定・ローダ（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートの検出は __file__ を基準に .git または pyproject.toml を探索して行うため、CWD に依存しない。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 読み込み順序: OS 環境変数 > .env.local > .env。既存の OS 環境変数は protected として上書きされない。
  - .env パーサは次の形式に対応:
    - コメント行（#）の扱い、`export KEY=val` フォーマット、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理など。
  - Settings クラスを提供し、以下の主要設定をプロパティ経由で取得可能:
    - J-Quants / kabu ステーション / LINE Messaging / DB パス（DuckDB, SQLite）/ 監視用パス（PID, kill flag）/ リソース閾値（CPU, Memory, Disk）/ 環境（development/paper_trading/live）とログレベル検証。
  - env/log_level の値検証と明確なエラーメッセージを実装。

- AI 関連（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）へバッチで問い合わせて各銘柄のセンチメントを ai_scores テーブルへ書き込む。
    - JST 時間ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を計算する calc_news_window を実装。DB 比較用に UTC naive datetime を返す。
    - バッチ処理: 最大 20 銘柄/回、1 銘柄あたり最大記事数と文字数でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - OpenAI への呼び出しは JSON Mode を使用し、レスポンスの厳密なバリデーション処理を実装（JSON 抽出、results 構造検査、型チェック、スコアの ±1.0 クリップ）。
    - ネットワークエラー/429/タイムアウト/5xx に対する指数的バックオフでのリトライと、失敗時のフェイルセーフ（スキップして処理継続）を実装。
    - テスト用に _call_openai_api をモック可能（unittest.mock.patch）。
    - DuckDB の executemany の制約（空リスト不可）を考慮して、DELETE/INSERT 前に空チェックを行う。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（Nikkei225 連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の market_regime を算出。
    - prices_daily と raw_news からデータを取得し、OpenAI（gpt-4o-mini）へ要求。API エラーやパース失敗時は macro_sentiment=0.0 にフォールバック。
    - ルックアヘッドバイアス対策として内部で datetime.today()/date.today() を参照せず、常に target_date を明示的に使用。
    - market_regime への書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実装。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を用いて PER, ROE を計算（EPS が 0/欠損のときは None）。
    - すべて DuckDB に対する SQL と Python の組合せで実装。外部 API や発注は行わない設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算。ホライズンは営業日ベースで検証（0 < h <= 252）。
    - calc_ic: ファクター値と将来リターンの Spearman（ランク）相関（IC）を計算。必要データが不足（有効レコード < 3）の場合は None を返す。
    - rank / factor_summary: ランク化ユーティリティ（同順位は平均ランク）および各ファクター列の基本統計量（count, mean, std, min, max, median）を提供。
    - 外部ライブラリ（pandas等）に依存せず標準ライブラリのみで実装。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
    - market_calendar が存在する場合は DB の値を優先。未登録日は曜日ベース（平日）でフォールバックする一貫性あるロジック。
    - calendar_update_job: J-Quants からカレンダー差分を取得して market_calendar を冪等に更新。バックフィルと健全性チェック（将来日付が過度に遠い場合はスキップ）を実装。
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult dataclass を実装（取得数/保存数/品質問題/エラー等を集約）。
    - 差分更新・バックフィル・品質チェック方針に基づいた設計を反映。
    - 内部ユーティリティ（テーブル存在確認、最大日付取得など）を実装。
  - etl モジュールで ETLResult を再エクスポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI や各種 API キーは環境変数（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）経由で取り扱う設計。鍵のデフォルト値は提供していません。

---

補足・設計上の注意
- ルックアヘッドバイアス防止: AI モジュール・リサーチモジュール等は datetime.today()/date.today() を使わず、必ず呼び出し側が target_date を明示して処理する設計です。
- DB 操作の冪等性: market_regime / ai_scores 等への書き込みは既存レコードを削除してから挿入する方式を取り、部分失敗時に他データを消してしまわないよう配慮しています。
- OpenAI 呼び出し: JSON Mode を前提に厳格なバリデーションとフェイルセーフ（API失敗時は 0.0 またはスキップ）を実装。テスト容易性のため _call_openai_api のモックポイントを用意しています。
- DuckDB 0.10 互換性: executemany に空リストを渡すとエラーとなる制約を考慮して、空チェックを挿入しています。

今後の予定（例）
- 戦略/実行/監視モジュールの実装（__all__ に宣言済のサブパッケージ群の充実）
- より詳細な品質チェックルールの追加
- CI テスト（DuckDB を用いた統合テスト、OpenAI 呼び出しのモック化など）

---
（この CHANGELOG はソースコードの内容から推測して作成しています。実際の変更履歴やリリースノートに合わせて適宜修正してください。）