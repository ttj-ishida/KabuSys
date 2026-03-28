CHANGELOG
=========

すべての注目すべき変更はここに記載します。  
形式は「Keep a Changelog」に準拠しています。

Unreleased
----------
（なし）

[0.1.0] - 2026-03-28
--------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージメタ情報: __version__ = "0.1.0"、パブリック API の __all__ を定義。

- 環境設定 / ロード
  - .env ファイルおよび環境変数から設定を読み込む設定モジュールを実装（kabusys.config）。
  - 自動ロードの探索はパッケージファイル位置からプロジェクトルート (.git / pyproject.toml) を検出する方式を採用し、CWD に依存しない挙動に。
  - .env のパースは以下に対応:
    - 空行 / コメント行（#）の無視
    - export KEY=val 形式のサポート
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理
    - クォート無しでのインラインコメント扱い（直前が空白/タブの場合に '#' をコメントと扱う）
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - Settings クラスを公開（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID、DBパス、環境名・ログレベル検証などのプロパティを提供）
  - 環境値検証（KABUSYS_ENV の許容値、LOG_LEVEL の許容値）と必須変数未設定時の ValueError を実装。

- データプラットフォーム（DuckDB ベース）
  - ETL 結果を扱うデータクラス ETLResult を実装（kabusys.data.pipeline / ETLResult を再エクスポートする kabusys.data.etl）。
  - ETL パイプライン基礎（差分取得、backfill、品質チェック連携）用ユーティリティ（kabusys.data.pipeline）を実装。DuckDB での日付最大取得やテーブル存在確認等を提供。
  - マーケットカレンダー管理モジュール（kabusys.data.calendar_management）を実装:
    - 営業日判定、前後営業日取得、期間内営業日リスト取得、SQ日判定のユーティリティを提供。
    - DB にカレンダーが無い場合は曜日ベース（土日除外）のフォールバックを行う堅牢な設計。
    - 夜間バッチ更新 job (calendar_update_job) を実装し、J-Quants クライアント経由で差分取得→冪等保存を行う（バックフィル・健全性チェック付き）。

- AI / ニュース解析
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）を実装:
    - 前日 15:00 JST ～ 当日 08:30 JST 相当の時間窓で raw_news / news_symbols を集約し、銘柄ごとに最大記事数・文字数でトリムして LLM に送信。
    - gpt-4o-mini（JSON Mode）を用いたバッチ処理（デフォルトバッチサイズ 20銘柄）。
    - リトライ（429, ネットワーク断, タイムアウト, 5xx）と指数バックオフ実装。
    - レスポンスの厳密バリデーション（JSON 抽出、results の存在確認、code/score の型検証、既知コードのみ採用）。
    - スコアを ±1.0 にクリップし、成功分のみ ai_scores テーブルに置換的に書き込む（DELETE → INSERT、部分失敗時の既存スコア保護）。
    - テスト用に OpenAI 呼び出しを差し替え可能に（_call_openai_api を patch で置換可能）。
  - 市場レジーム判定（kabusys.ai.regime_detector）を実装:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、ニュース NLP によるマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定。
    - マクロニュースはニュース NLP のウィンドウ集計を再利用して取得。LLM 呼び出しは gpt-4o-mini を使用。
    - API 呼び出し失敗時のフォールバック（macro_sentiment=0.0）、堅牢なリトライ・パースエラーハンドリングを実装。
    - 計算結果は market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT、ROLLBACK の安全処理）。

- リサーチ（ファクター計算・特徴探索）
  - ファクター計算群（kabusys.research.factor_research）を実装:
    - Momentum: 約1M/3M/6M リターン、200日移動平均乖離（ma200_dev）。データ不足時は None を返す設計。
    - Volatility / Liquidity: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - Value: raw_financials から最新財務（target_date 以前）を取り出し PER・ROE を計算（EPS が 0/欠損時は None）。
    - DuckDB SQL を活用し、外部 API に依存しない設計。
  - 特徴量探索（kabusys.research.feature_exploration）を実装:
    - 将来リターン calc_forward_returns（任意ホライズン、入力検証あり）。
    - IC（Information Coefficient）計算 calc_ic（スピアマンのランク相関、有効レコード数チェック）。
    - ランク変換ユーティリティ rank（同順位は平均ランク）。
    - factor_summary：各ファクター列の count/mean/std/min/max/median を計算。
    - pandas 等に依存せず標準ライブラリ + DuckDB で実装。

Changed
- 初期リリースにおいて実装上の設計上注意点・方針を明記（ルックアヘッドバイアス回避、DuckDB 互換性、部分失敗時の DB 保護など）。

Fixed
- （初版のため該当なし。実装では多くのフェイルセーフとエラーハンドリングを導入）

Security
- 環境変数の読み込み/上書きに際して OS 環境変数を保護する protected セットを導入（.env 上書き時の安全性確保）。

Internal / Implementation Notes
- OpenAI クライアントは OpenAI API（OpenAI クラス）を直接生成して使用。テスト容易性のため内部 _call_openai_api を patch 置換可能に設計。
- DuckDB への書き込みはトランザクション方式で冪等性を担保（BEGIN/DELETE/INSERT/COMMIT）。失敗時は ROLLBACK を試行し失敗ログを WARN 出力。
- executemany に空リストを渡すと問題となる DuckDB の挙動を考慮し、空パラメータを明示的にチェックしてスキップ。
- 時刻・日付の扱いはすべて date / naive UTC datetime 等に統一し、タイムゾーン混入や datetime.today() によるルックアヘッドを避ける設計。

Breaking Changes
- なし（初回リリース）

Notes / Migration
- 本バージョンは初期実装フェーズのため、OpenAI API キー、J-Quants トークン、Kabu API パスワード、Slack トークン等の環境変数設定が必須です。設定名は Settings のプロパティ名に対応しています（例: JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
- .env の自動ロードはプロジェクトルート検出に依存するため、配布後に動作させる場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使い手動で設定注入するか、正しく .env をプロジェクトルートに配置してください。