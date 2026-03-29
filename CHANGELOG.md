# Changelog

すべての注目すべき変更点をここに記録します。  
このファイルは Keep a Changelog のガイドラインに従って作成されています。  

注記: 以下の変更点はリポジトリ内のコードから推測して記載しています。実際の変更履歴はコミットログ等をご確認ください。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-29

初期リリース。日本株自動売買プラットフォーム "KabuSys" の基礎機能を実装しました。主な追加点は以下のとおりです。

### Added
- パッケージ基盤
  - パッケージのメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージ公開インターフェースを定義（data, strategy, execution, monitoring を __all__ に追加）。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイル（.env, .env.local）および環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して決定（CWD 非依存）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）。
  - .env パーサーは以下に対応：
    - コメント行、空行を無視。
    - export KEY=val 形式をサポート。
    - シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い（クォート有り/無しで挙動を分けて安全に解析）。
    - OS の既存環境変数を保護するため、上書きポリシー（override / protected）を実装。
  - 必須環境変数チェック（_require）と Settings クラスを提供：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等を必須として取得。
    - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL のバリデーションを実装。
    - データベースパスのデフォルト（DUCKDB_PATH: data/kabusys.duckdb, SQLITE_PATH: data/monitoring.db）を提供。

- データ（kabusys.data）
  - 市場カレンダー管理（calendar_management）
    - market_calendar テーブルを用いた営業日判定ロジックを実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録ありの場合は DB 値を優先、未登録日は曜日ベースでフォールバックする一貫した振る舞い。
    - 夜間バッチジョブ calendar_update_job を実装（J-Quants API から差分取得して保存、バックフィル・健全性チェックあり）。
    - 最大探索日数やバックフィル日数等の安全パラメータを導入して無限ループ等を防止。
  - ETL パイプライン（pipeline）
    - ETLResult データクラスを公開し、ETL 処理の取得数/保存数、品質チェック結果、エラー等を集約可能に。
    - 差分更新、バックフィル（デフォルト 3 日）、品質チェックの設計方針をコードに反映。
    - DuckDB を用いたテーブル存在チェックや最大日付取得ユーティリティを実装。
  - ETL インターフェースの再エクスポート（data.etl → ETLResult）。

- 研究・因子（kabusys.research）
  - factor_research
    - モメンタム、バリュー、ボラティリティ／流動性関連ファクターを実装：
      - calc_momentum: 1M/3M/6M リターンと 200 日移動平均乖離（ma200_dev）計算。
      - calc_value: raw_financials から最新の EPS / ROE を取得して PER / ROE を算出（EPS=0/欠損時は None）。
      - calc_volatility: 20 日 ATR（true range の扱いに注意）・相対 ATR（atr_pct）・20 日平均売買代金・出来高比率を計算。
    - DuckDB を活用したウィンドウ関数で実装。データ不足時は None を返す設計。
  - feature_exploration
    - calc_forward_returns: 将来リターン（デフォルト: 1/5/21 営業日）を一括で取得する SQL 実装。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算し、データ不足時は None を返す。
    - rank: 同順位は平均ランクで扱うランク関数（浮動小数丸めで ties 検出を安定化）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を算出。
  - re-export: zscore_normalize を含むユーティリティのエクスポート。

- AI（kabusys.ai）
  - ニュース NLP スコアリング（news_nlp）
    - raw_news / news_symbols テーブルを参照し、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）の JSON Mode でバッチ評価。
    - 時間ウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（内部では UTC naive datetime を使用）。
    - バッチ処理: 最大 20 銘柄/回、1 銘柄あたり最新 10 記事・最大 3000 文字でトリム。
    - 再試行ロジック: 429・ネットワーク断・タイムアウト・5xx に対して指数バックオフリトライを実装。
    - レスポンスのバリデーションとスコアの ±1.0 クリップ。部分成功時でも既存スコアを保護するためコードを絞って DELETE→INSERT。
    - テスト容易性: _call_openai_api を patch で差し替え可能。
  - 市場レジーム判定（regime_detector）
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とニュースマクロセンチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロセンチメントは news_nlp と類似する手法でタイトルを LLM に投げ JSON で取得。API 失敗時は macro_sentiment=0.0 でフェイルセーフ。
    - レジームスコアはクリップされ、結果を market_regime テーブルへ冪等（BEGIN/DELETE/INSERT/COMMIT）で保存。
    - OpenAI 呼び出しは専用の内部実装でモジュール間カップリングを抑制。
    - リトライ・エラー処理、JSON パースの堅牢化を実装。

- ロギングとフォールトトレランス
  - 各モジュールで詳細なログ（info/debug/warning/exception）を追加。失敗時は可能な限りフェイルセーフ挙動（例: LLM エラーは 0.0 戻し、部分書き込みで既存データを保護）を採用。
  - DuckDB に対する executemany の空リスト取り扱い等、実装依存の注意点に合わせたガードを実装。

### Design / Implementation Notes (設計上の重要点)
- ルックアヘッドバイアス防止:
  - date.today() / datetime.today() などを直接参照せず、target_date 引数ベースで計算を行う設計（backtesting/研究用途に配慮）。
  - prices_daily などのクエリで target_date 未満 / 排他条件を使用。
- DB 書き込みは冪等性を意識（ON CONFLICT / DELETE→INSERT / トランザクション制御）。
- テスト容易性:
  - OpenAI 呼び出し箇所は内部の _call_openai_api を patch できるようにしてユニットテストで差し替え可能。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により環境依存の自動 .env 読み込みを抑制可能。
- 外部依存:
  - DuckDB を主なローカル DB として利用。
  - OpenAI（gpt-4o-mini）を外部 LLM として利用（JSON Mode を期待）。
  - J-Quants クライアントは data.jquants_client を想定（fetch/save メソッド呼び出し箇所あり）。

### Security / Required Environment Variables
- 本機能群を動かすために最低限必要となる環境変数（Settings 参照）:
  - OPENAI_API_KEY (LLM 呼び出し時、関数引数でも注入可能)
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- .env の自動ロード時に OS 環境変数を保護する仕組みを導入。

### Known limitations / TODO（コードから推測される注意点）
- 一部のファクター（PBR・配当利回りなど）は未実装（calc_value の docstring より）。
- DuckDB のバージョン差異（list 型バインドの挙動）に対する互換性ガードが存在するため、環境依存の差異に注意が必要。
- OpenAI レスポンスの形式に厳密に依存しているため、API 側仕様変更への影響を受ける可能性あり（堅牢化ロジックは追加済み）。

---

内部実装に基づく要約は以上です。追加でバージョン履歴の細分化（例: minor/patch リリースの履歴）や各関数・モジュール毎の変更理由を含めた詳細な CHANGELOG を希望される場合は、その観点（例えば「AI モジュールの挙動」「ETL の堅牢化」等）を指定してください。