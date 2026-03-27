KEEP A CHANGELOG 準拠の形式で、コードベースから推測される変更点を記載した CHANGELOG.md（日本語）を作成しました。

なお本リリースはパッケージの __version__ = "0.1.0" に合わせて初回リリースとして記載しています（リリース日を現在日付にしています）。内容はソースコードの実装から推測してまとめた要約です。

CHANGELOG.md
=============
全般方針
--------
- 本ドキュメントは "Keep a Changelog" の記法に準拠しています。
- 各項目はソースコードの実装内容から推定して記載しています。

Unreleased
----------
- （次のリリースでの変更をここに記載します）

0.1.0 - 2026-03-27
------------------
Added
- パッケージ初回公開（kabusys v0.1.0）。
- パッケージトップ:
  - pkg: kabusys.__init__ を追加しバージョン情報と公開サブパッケージ一覧を定義。
- 設定管理（kabusys.config）:
  - .env ファイルまたは環境変数から設定を自動読み込みする機能を実装。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を基準として探索）。
  - .env パーサを実装:
    - 空行・コメント行（#）を無視。
    - export KEY=val 形式をサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープに対応して正しく値を復元。
    - クォートなしの場合の行内コメント認識を実装（# の前が空白/タブの場合のみコメント扱い）。
  - 自動ロードの優先順位: OS 環境 > .env.local（上書き） > .env（未設定時設定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロード無効化可能。
  - Settings クラスを公開（プロパティで必須パラメータを取得、未設定時に ValueError を送出）:
    - J-Quants、kabuステーション、Slack、DBパス（DuckDB/SQLite）、環境（development/paper_trading/live）や LOG_LEVEL 等を扱う。
    - env と log_level の値検証（許容値チェック）を実装。
- データモジュール（kabusys.data）:
  - ETL 用インターフェースの公開（ETLResult を再エクスポート）。
  - calendar_management:
    - JPX マーケットカレンダー管理機能を実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days といった営業日判定ユーティリティを提供。
    - market_calendar テーブルの有無に応じた「DB 優先」＋「曜日ベースのフォールバック」ロジックを実装。
    - 夜間バッチ calendar_update_job を実装（J-Quants API から差分取得して冪等保存。バックフィル・健全性チェックあり）。
    - DuckDB から返る日付の安全な date 変換を実装。
  - pipeline（ETL パイプライン）:
    - ETLResult dataclass を実装（取得件数・保存件数・品質問題・エラー集約）。
    - 差分更新、バックフィル、品質チェック（quality モジュールとの連携）を想定したユーティリティを実装（内部関数でテーブル存在チェック／最大日付取得等）。
    - DuckDB の互換性を考慮した実装（executemany の空リスト回避など）。
- AI モジュール（kabusys.ai）:
  - news_nlp:
    - raw_news と news_symbols を用いてニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）で銘柄別センチメント評価を行い ai_scores テーブルへ書き込む処理を実装。
    - ニュースの時間ウィンドウ定義（JST 基準の前日 15:00 〜 当日 08:30 を UTC に変換して使用）。
    - 1チャンクあたりのバッチ処理（デフォルト最大 20 銘柄）、1銘柄あたり最大記事数（10）と文字数制限（3000 文字）を実装。大きなテキストはトリム。
    - OpenAI 呼び出しは JSON mode を使いレスポンスを厳密にバリデーションして結果を抽出。
    - 429（レート制限）・ネットワーク断・タイムアウト・5xx を対象に指数バックオフでリトライ。非再試行例外はスキップして処理継続するフェイルセーフ設計。
    - レスポンス検証: JSON パース復元（前後余計なテキストが混ざるケースの {} 抽出）、results リストの型検証、コードが要求セットに含まれるか、スコアが有限な数値か等をチェック。スコアは ±1.0 にクリップして保存。
    - DuckDB への書き込みは、部分失敗時に既存スコアを保護するため対象コードのみ DELETE → INSERT する方式を採用。
  - regime_detector:
    - ETF(1321) の200日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次で判定する処理を実装。
    - ma200_ratio 計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを排除。データ不足時は中立値（1.0）にフォールバックして警告ログ出力。
    - マクロニュース抽出はキーワードベース（複数キーワードの ILIKE 検索）で最新 N 件（最大 20）を取得。
    - OpenAI（gpt-4o-mini）で macro_sentiment を JSON として取得。API エラー時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。リトライ・エラーハンドリングを実装。
    - レジームスコア合成式と閾値（bull/bear 判定用）を実装。結果は market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、エラー時は ROLLBACK を試行）。
    - news_nlp との結合を避ける設計（OpenAI 呼び出し関数は別実装）でモジュールの独立性を保持。
- Research モジュール（kabusys.research）:
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA（ma200_dev）を計算。データ不足時の None ハンドリング。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比率（volume_ratio）を計算。true_range の NULL 伝播を制御して正確に集計。
    - calc_value: raw_financials から最新財務（target_date 以前）を取得して PER、ROE を計算。
    - 実装は DuckDB の SQL と Python の組合せで行い、prices_daily / raw_financials のみ参照する非侵襲的設計。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD を用いて一括計算。horizons の検証（正の整数かつ 252 以下）を実装。
    - calc_ic: Spearman のランク相関（Information Coefficient）を実装。結合・欠損除外・同順位は平均ランクで処理。有効レコードが 3 未満なら None を返す。
    - rank: 同順位は平均ランクを割当てる実装（丸めで ties 検出の安定化）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー機能を提供。
  - research パッケージは主要関数を再エクスポートして使いやすくしている（calc_momentum, calc_value, calc_volatility, zscore_normalize 等）。
- 実装上の設計方針・品質点:
  - ルックアヘッドバイアス回避: 各モジュールは datetime.today() / date.today() を内部で直接参照せず、必ず target_date を引数として受ける設計。
  - フェイルセーフ: 外部 API（OpenAI / J-Quants）呼び出し失敗時は例外をそのまま上げる箇所と、ローカルで安全値にフォールバックして処理を継続する箇所を使い分けている（ニュース/レジームスコアはスコア 0.0 にフォールバック等）。
  - DuckDB 互換性考慮: executemany の空リスト不可など DuckDB 固有の注意点に合わせた実装。
  - DB 書き込みは冪等性を重視（DELETE → INSERT、ON CONFLICT による上書きなど）。
  - OpenAI への呼び出しは JSON mode を使用し、返却 JSON の堅牢なパースと検証、指数バックオフでのリトライ（429, ネットワーク, タイムアウト, 5xx）を実装。
  - ロギング: 重要な分岐やフォールバック・警告は logger を通して情報出力する実装。

Changed
- 初回リリースのため "Changed" の履歴は無し（今後のリリースで差分を記載）。

Fixed
- 初回リリースのため "Fixed" の履歴は無し。

Deprecated
- 初回リリースのため無し。

Removed
- 初回リリースのため無し。

Security
- 機密情報管理:
  - OpenAI API キーや各種トークンは Settings 経由で必須チェックを行い、.env/環境変数由来で扱う設計。
  - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD を提供（テストや CI 用の考慮）。

補足（実装上の注記・推測）
- OpenAI SDK を直接利用する箇所で client.chat.completions.create(..., response_format={"type": "json_object"}) を使用しており、JSON モードでの一貫したレスポンス取得を想定している。
- news_nlp と regime_detector はそれぞれ独立した OpenAI 呼び出しラッパーを持ち、テスト時はそれらをモックしやすい設計（関数をパッチ差替えできるように実装）。
- jquants_client（kabusys.data.jquants_client）は外部 API クライアントとして参照されているが、実装はソースに含まれていないため fetch/save の詳細は外部依存と推定。
- monitoring / execution などのサブパッケージは __all__ に含まれているが、今回提供されたファイル群には実装が含まれていない。次版での追加が想定される。

ライセンス／ソース
- この CHANGELOG の内容は提供されたソースコードの実装から推測して作成しています。実際のリポジトリやドキュメントと差異がある場合は、公式ソースに従って更新してください。