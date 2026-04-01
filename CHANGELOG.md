CHANGELOG
=========

すべての注目すべき変更はここに記載します。本ファイルは Keep a Changelog の形式に準拠しています。
バージョン番号はセマンティックバージョニングに従います。

[Unreleased]
-------------

（なし）

[0.1.0] - 2026-04-01
--------------------

Added
- パッケージ初期リリース (kabusys 0.1.0)
  - パッケージエントリポイント:
    - src/kabusys/__init__.py: バージョン定義と公開モジュール一覧（data, strategy, execution, monitoring）。
  - 環境変数・設定管理:
    - src/kabusys/config.py:
      - .env / .env.local 自動読み込み機能（プロジェクトルートは .git または pyproject.toml を探索して決定）。
      - export KEY=val 形式やクォート、インラインコメントを考慮した .env パース実装。
      - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD フラグ。
      - Settings クラスを通じた型付き設定アクセス（J-Quants / kabuステーション / Slack / DB パス /監視閾値 / 環境判定 / ログレベルなど）。
      - 必須変数未設定時に ValueError を投げる _require ヘルパー。
  - AI モジュール:
    - src/kabusys/ai/news_nlp.py:
      - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini・JSON mode）で銘柄別センチメントをスコア化し ai_scores に書き込む機能。
      - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）の計算（calc_news_window）と記事トリム（最大記事数・最大文字数）。
      - バッチ処理（最大 20 銘柄/チャンク）、リトライ（429/ネットワーク/5xx の指数バックオフ）、レスポンス検証、スコア ±1.0 クリップ。
      - フェイルセーフ設計（API 失敗時は該当チャンクをスキップして他銘柄を保護）、DuckDB の executemany 空リスト制約を考慮した実装。
      - ユニットテスト用に _call_openai_api をパッチ可能に設計。
    - src/kabusys/ai/regime_detector.py:
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime に冪等書き込みする機能。
      - マクロ記事抽出、OpenAI 呼び出し（gpt-4o-mini）、JSON パース、リトライ・バックオフ、API エラー時のフォールバック（macro_sentiment=0.0）を備えた堅牢な実装。
      - ルックアヘッドバイアス防止設計（date < target_date 等の排他条件、datetime.today() を参照しない）。
  - Data / ETL / カレンダー:
    - src/kabusys/data/pipeline.py:
      - ETLResult データクラス（ETL の取得/保存数、品質問題、エラーログを保持）。to_dict により品質問題を辞書化。
      - ETL パイプライン設計方針を反映したヘルパー（差分更新、バックフィル、品質チェックフラグ等）。
    - src/kabusys/data/etl.py:
      - pipeline.ETLResult の再エクスポート（public API）。
    - src/kabusys/data/calendar_management.py:
      - market_calendar を用いた営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）と夜間バッチ更新 job（calendar_update_job）。
      - DB 登録値優先・未登録日は曜日ベースのフォールバック、最大探索日数やバックフィル日数、健全性チェックを実装。
      - J-Quants クライアントを利用した差分取得および冪等保存呼び出しをサポート。
  - Research（因子・特徴量解析）:
    - src/kabusys/research/factor_research.py:
      - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、出来高/売買代金指標）、Value（PER, ROE）等のファクター計算関数（calc_momentum, calc_volatility, calc_value）。
      - DuckDB 上で SQL を用いて効率的に計算する実装（外部 API へはアクセスしない）。
    - src/kabusys/research/feature_exploration.py:
      - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリ（factor_summary）を提供。
      - 外部依存を持たないスタンドアロン実装（標準ライブラリのみ）。
    - src/kabusys/research/__init__.py:
      - 主要関数の再エクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。
  - 内部ユーティリティ:
    - DuckDB の日付型変換・テーブル存在チェック、各モジュール共通の設計（冪等性、ロールバック処理、ログ出力など）。
  - テスト親和性:
    - OpenAI 呼び出しやその他外部相互作用のエントリをモック／パッチ可能に設計（_call_openai_api の差し替え等）。

Changed
- N/A（初回リリース）

Fixed
- N/A（初回リリース）

Security
- 環境変数読み込み時に OS 環境変数を保護する機構（.env による上書きを protected set で制御）。
- OpenAI API キー未設定時は明示的に例外を発生させ、暗黙の失敗を防止。

Notes / Implementation details
- 全体設計で「ルックアヘッドバイアス防止」を積極採用（datetime.today()/date.today() の不適切な直接参照回避、DB クエリにおける排他境界）。
- OpenAI へのリクエストは JSON Mode を利用し、レスポンスの堅牢なパースとバリデーションを実装。API エラーはリトライまたはフェイルセーフ（0.0 やチャンクスキップ）で対処。
- DuckDB 特有の挙動（executemany に空リスト不可、日付型の取り扱いなど）を考慮したコードパスを導入。
- 外部 API クライアント（J-Quants, OpenAI）は明示的に注入／生成する形で実装され、ユニットテストの差し替えを容易にしている。

お問い合わせ
- バグ報告や改善要望は Issue を作成してください。