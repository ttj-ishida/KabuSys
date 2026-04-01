CHANGELOG
=========

すべての変更は Keep a Changelog の方針に準拠して記載しています。
日付はリリース日（推定）です。コード内容から推測して要点をまとめています。

Unreleased
----------

Note:
- 現状のコードベースに対して検出した「既知の問題 / 要注意点」を記載しています。
  次のリリースで対応することを推奨します。

Added
- pipeline._get_max_date の末尾が切れている箇所が見つかりました（src/kabusys/data/pipeline.py）。
  - この関数の最後が "return date.fro" で途切れており、実行時エラーや型エラーの原因になります。
  - 修正案: DuckDB から返る型の扱いを完了させ、MAX 日付が None の場合の返り値を適切に返すよう実装してください。

Changed
- なし（Unreleased）

Fixed
- なし（Unreleased）

Security
- なし（Unreleased）

[0.1.0] - 2026-04-01
--------------------

Added
- 初期リリース。パッケージのコア機能を実装。
  - パッケージ初期化:
    - src/kabusys/__init__.py にてバージョン "0.1.0" を設定。公開サブパッケージとして data, strategy, execution, monitoring を __all__ に指定。
  - 環境変数 / 設定管理:
    - src/kabusys/config.py を追加。
    - .env / .env.local の自動読み込み機構（プロジェクトルート検出: .git または pyproject.toml）。
    - .env パーサの強化: コメント、export プレフィックス、シングル/ダブルクォートとエスケープシーケンス、インラインコメント処理に対応。
    - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - Settings クラスを提供し、J-Quants・kabu・Slack・DBパス・監視閾値・環境モード・ログレベル等のプロパティを定義。必須項目は _require() で検査。
    - 環境変数の保護（OS 環境変数のキーは .env.local で上書きされない等）を考慮したロードロジック。
  - AI（ニュース NLP / レジーム判定）:
    - src/kabusys/ai/news_nlp.py
      - raw_news / news_symbols を集約し銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）に対してバッチ（最大 20 銘柄）で JSON Mode を用いてセンチメント評価。
      - チャンク/記事トリム（1銘柄あたり最大記事数・最大文字数）によるトークン管理。
      - 再試行（429, ネットワーク断, タイムアウト, 5xx）を指数バックオフで実装。応答バリデーション（JSON 抽出、results フォーマット、既知コードフィルタ、数値チェック）を行いスコアを ±1.0 にクリップ。
      - DuckDB への書き込みは冪等（対象コードのみ DELETE → INSERT）で部分失敗時に既存データを保護。
      - テストフック: _call_openai_api を patch できる設計。
    - src/kabusys/ai/regime_detector.py
      - ETF 1321（Nikkei 225 連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロニュースセンチメント（重み 30%）を合成して市場レジームを判定（'bull'/'neutral'/'bear'）。
      - ma200_ratio の計算は target_date 未満のデータのみ使用（ルックアヘッドバイアス対策）。
      - マクロニュース抽出、LLM 呼び出し（gpt-4o-mini）で macro_sentiment を取得。API 失敗時は 0.0 にフォールバック。
      - 結果を market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
      - テストフック: _call_openai_api を patch できる設計。
  - Data / ETL / カレンダー / 品質管理:
    - src/kabusys/data/pipeline.py, etl.py, calendar_management.py を実装。
      - ETLResult dataclass を公開（etl.py で再エクスポート）。
      - pipeline: 差分更新、バックフィル、品質チェックの枠組みを実装（J-Quants クライアント呼び出し、保存、quality モジュール連携）。
      - calendar_management: market_calendar を使った営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。DB データ優先、未登録日は曜日ベースのフォールバック。calendar_update_job で J-Quants から差分取得し保存（バックフィル / 健全性チェック含む）。
  - Research（ファクター計算 / 特徴量探索）:
    - src/kabusys/research/factor_research.py
      - Momentum（1M/3M/6M リターン、ma200 偏差）、Volatility（20日 ATR、相対 ATR、20日平均売買代金）、Value（PER, ROE）を DuckDB SQL ウィンドウ関数で実装。入力は prices_daily や raw_financials。
      - 計算結果は (date, code) をキーとする dict のリストで返却。
    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算 calc_forward_returns（任意ホライズン、入力バリデーションあり）。
      - IC（Spearman）の計算 calc_ic、rank、factor_summary（count/mean/std/min/max/median）を実装。外部ライブラリに依存しない純粋 Python 実装。
  - Utilities / パッケージ構成
    - src/kabusys/ai/__init__.py は score_news を明示的に公開。
    - src/kabusys/research/__init__.py で各種計算関数を公開。
    - DuckDB ベースでのローカル分析基盤を前提にした実装（DuckDB 接続を受け取る API）。

Changed
- なし（初期リリース）

Fixed
- .env パースのエッジケースに対応（クォート内のバックスラッシュエスケープ、インラインコメントの取り扱いなど）を実装。

Security
- 環境変数の必須項目（OpenAI, Slack, kabu 等）は明示的にチェックし、未設定時は ValueError を発生させる安全設計を採用。

Notes / Known limitations
- pipeline._get_max_date の末尾が不完全（"return date.fro"）であり、実行時に例外が発生します。リリース直後の重大バグとして修正が必要です。
- src/kabusys/ai/__init__.py では news_nlp.score_news のみをエクスポートしていますが、regime_detector は明示的に __all__ に含まれていません。API 公開意図に注意してください（意図的切り分けの可能性あり）。
- 一部モジュールは外部 API（OpenAI, J-Quants）や DuckDB 環境を前提としており、環境が未整備だと実行できません。テストしやすいように _call_openai_api 等の差し替えポイントが用意されています。
- 日時の扱いに関して全体的にルックアヘッドバイアスを避ける設計（datetime.today() を内部処理で参照しない）になっています。外部から渡す target_date を正しく与えてください。

Upgrade / Migration notes
- 環境変数の設定:
  - OpenAI: OPENAI_API_KEY（もしくは score_* 関数に api_key 引数を渡す）
  - J-Quants: JQUANTS_REFRESH_TOKEN
  - kabu station: KABU_API_PASSWORD （KABU_API_BASE_URL はデフォルト localhost）
  - Slack: SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- .env の自動読み込みを一時的に無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- DuckDB のテーブルスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など）を事前に用意してください。コードはこれらの存在を前提にしています。

ライセンス / 著作権
- この CHANGELOG はコード内容から推測して作成したものであり、実際のコミット履歴ではありません。正確な履歴を残す場合は Git のコミットログから正式な CHANGELOG を生成することを推奨します。