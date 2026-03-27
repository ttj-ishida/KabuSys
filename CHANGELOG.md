Changelog
=========

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog の形式に準拠しています。

フォーマット:
- すべてのリリースは日付順（新しい順）で記載されています。
- 各リリースは主要なカテゴリ（Added, Changed, Fixed, Deprecated, Removed, Security）に分類しています。

[Unreleased]
------------

（未リリースの変更はここに記載します）

[0.1.0] - 2026-03-27
-------------------

初回リリース。KabuSys のコア機能群を提供する最初の実装を追加しました。
以下は主要な追加内容と実装上の注意点です。

Added
- パッケージ初期化
  - src/kabusys/__init__.py
    - パッケージメタ情報と公開サブパッケージ名を定義（data, strategy, execution, monitoring）。
    - バージョン: 0.1.0

- 環境変数 / 設定管理
  - src/kabusys/config.py
    - Settings クラスを実装し、アプリケーション設定を環境変数から取得するプロパティを提供。
      - 必須設定: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - オプション設定とデフォルト値: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL の検証
    - .env 自動読み込み機能を実装（読み込み優先順位: OS 環境 > .env.local > .env）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能（テスト用）。
      - .env パーサは export KEY=val 形式、シングル/ダブルクォート、エスケープ、インラインコメントを考慮。
      - 読み込み時に OS 側の既存環境変数を保護する仕組みを導入（protected set）。
    - 必須値が未設定の場合は明示的に ValueError を出す _require 関数を提供。

- データ処理 / カレンダー
  - src/kabusys/data/calendar_management.py
    - JPX（市場）カレンダー管理機能を追加。
      - 営業日判定: is_trading_day, is_sq_day
      - 翌/前営業日取得: next_trading_day, prev_trading_day
      - 期間内営業日列挙: get_trading_days
      - カレンダーの夜間更新バッチ: calendar_update_job（J-Quants API 経由で差分取得して保存）
    - 実装上の配慮:
      - market_calendar テーブルが未取得の場合は曜日（平日）ベースでフォールバック。
      - DB 登録値は優先。未登録日は曜日ベースで一貫したフォールバックを適用。
      - 探索は _MAX_SEARCH_DAYS により上限を設け無限ループを防止。
      - バックフィルや健全性チェックを含む。

  - src/kabusys/data/etl.py, src/kabusys/data/pipeline.py
    - ETL パイプラインのインターフェースと主要ロジックを追加。
      - ETLResult データクラスを公開（取得件数、保存件数、品質問題一覧、エラー一覧などを保持）。
      - 差分取得、バックフィル、品質チェック（quality モジュール連携）を想定した設計。
      - DuckDB のテーブル存在チェック、最大日付取得ユーティリティなどを実装。
      - エラーや品質問題は収集して上位へ伝搬させる設計（Fail-Fast ではなく呼び出し元で判断）。
      - J-Quants クライアント（jquants_client）を利用する想定で実装。

- AI（NLP）機能
  - src/kabusys/ai/news_nlp.py
    - ニュース記事を銘柄ごとに集約して OpenAI（gpt-4o-mini）へ送り、銘柄別センチメント（ai_score）を算出する機能を追加。
      - タイムウィンドウは JST 基準で「前日 15:00 ～ 当日 08:30」を採用（内部では UTC naive datetime を返す calc_news_window を提供）。
      - 1 銘柄あたり最大記事数・最大文字数でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
      - 最大 20 銘柄を 1 バッチで送信（_BATCH_SIZE）。
      - OpenAI の JSON Mode を活用し、レスポンスの厳密なバリデーションを実施（_validate_and_extract）。
      - リトライ / エクスポネンシャルバックオフ対応（RateLimit, ネットワーク断, タイムアウト, 5xx）。
      - スコアは ±1.0 にクリップ。部分失敗時に既存データを保護するため対象コードのみを DELETE→INSERT で置換。
      - テスト容易性のため _call_openai_api を patch で置き換え可能に実装。

  - src/kabusys/ai/regime_detector.py
    - 市場レジーム（bull / neutral / bear）判定ロジックを追加。
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成。
      - マクロニュース抽出はキーワードベース（_MACRO_KEYWORDS）で raw_news からタイトルを取得。
      - OpenAI（gpt-4o-mini）によりマクロセンチメントを JSON で取得。API 失敗時は macro_sentiment=0.0 でフェイルセーフ。
      - 最終スコアは所定の閾値でラベル化（_BULL_THRESHOLD, _BEAR_THRESHOLD）。
      - DB へは冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
      - テスト用に _call_openai_api を patch で差し替え可能。

- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py
    - ファクター計算モジュールを追加（StrategyModel.md に沿った実装）。
      - Momentum: mom_1m / mom_3m / mom_6m、ma200_dev（200日移動平均乖離）
      - Volatility / Liquidity: 20日 ATR（atr_20）、atr_pct、avg_turnover、volume_ratio
      - Value: per（price / eps）、roe（raw_financials から取得）
      - 各関数は DuckDB を用いた SQL 実行により計算し、(date, code) 単位の辞書リストを返す。
      - データ不足時は None を返すように設計。

  - src/kabusys/research/feature_exploration.py
    - 研究向けユーティリティを追加。
      - 将来リターン計算: calc_forward_returns（horizons 指定可、デフォルト [1,5,21]）
      - IC（Information Coefficient）計算: calc_ic（スピアマンランク相関）
      - 統計サマリー: factor_summary（count/mean/std/min/max/median）
      - ランク関数: rank（同順位は平均ランク）
    - 外部依存を用いず標準ライブラリと DuckDB のみで実装。

  - src/kabusys/research/__init__.py
    - 主要関数を再エクスポート（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

- データユーティリティ
  - src/kabusys/data/__init__.py
    - data パッケージのプレースホルダ（サブモジュールの公開はそれぞれのモジュールで行う想定）。

- その他
  - モジュール間の設計方針を明文化（ソースの docstring に記載）
    - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない設計（target_date を引数で渡すスタイル）。
    - OpenAI 呼び出しはモジュール毎に独立した _call_openai_api を定義し、モジュール間で private 関数を共有しない。
    - DuckDB の制約（executemany に空リストを渡せない等）に対応した実装上の注意点を反映。
    - DB 書き込みは可能な限り冪等に（DELETE→INSERT 等）設計。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。
  - 注意点: OpenAI API キーは引数で注入可能かつ環境変数 OPENAI_API_KEY で解決される。秘密情報の取り扱いは環境変数管理に注意。

Notes / マイグレーション / テストについて
- テスト容易性
  - OpenAI への外部呼び出しは各モジュールの _call_openai_api を unittest.mock.patch により差し替え可能。
  - .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化できるため、テスト環境での副作用を抑制可能。
- DuckDB に関する注意
  - executemany に空リストを渡すとエラーになるバージョンがあるため、実装中で空チェックを行っている。
- 設計方針の強調
  - ルックアヘッドバイアス防止のため、全ての「当日参照」ロジックは target_date を明示的に受け取る形。
  - 外部 API の失敗は原則フェイルセーフ（0.0 等の中立値にフォールバック）してパイプライン全体の停止を防ぐ設計。

お問い合わせ
- 本リリースに関する質問やバグ報告はリポジトリの issue を作成してください。