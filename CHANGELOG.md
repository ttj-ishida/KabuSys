CHANGELOG
=========

すべての注目すべき変更はこのファイルで管理します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用しています。

Unreleased
----------

（現在未リリースの変更はここに記載します）

[0.1.0] - 2026-03-28
-------------------

初回リリース。日本株自動売買 / 研究・データ基盤のコア機能群を実装しています。

Added
- パッケージ基盤
  - kabusys パッケージ初期バージョンを公開（__version__ = "0.1.0"）。
  - パッケージの公開 API として data, strategy, execution, monitoring をエクスポート。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード:
    - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - .env 読み込み時に既存 OS 環境変数は保護（protected）して上書きを制御。
  - .env パーサーは以下をサポート:
    - export KEY=val 形式
    - シングル/ダブルクォート、バックスラッシュエスケープ
    - インラインコメント処理（クォート外での '#' の扱い）
  - 必須設定を取得する _require 関数と、env / log_level の検証（有効値チェック）を実装。
  - データベースパス（DuckDB / SQLite）、Slack / kabuStation / J-Quants 関連の設定プロパティを提供。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を処理して銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む機能を実装（score_news）。
    - 対象時間ウィンドウの計算（JST 前日 15:00 ～ 当日 08:30 の UTC 変換）を提供。
    - 銘柄ごとに最新記事を集約し（上限記事数・文字数でトリム）、最大 _BATCH_SIZE（20）ごとにバッチで OpenAI（gpt-4o-mini）に送信。
    - JSON Mode を利用した堅牢なレスポンス検証（パース、results フィールド、型チェック、未知コードの無視、スコアの数値検証、±1.0 でクリップ）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。回復不能な場合はスキップ（フェイルセーフ）。
    - テスト容易性: _call_openai_api の差し替え（patch）を想定。
    - DB への書き込みは部分失敗リスクを抑えるため、スコア取得に成功したコードのみ削除・挿入（DELETE per-code → INSERT）する冪等処理を実装。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定（score_regime）。
    - DuckDB からの価格・ニュース取得、マクロニュース抽出、OpenAI 呼び出し、スコア合成、market_regime テーブルへの冪等書き込みを実装。
    - LLM 呼び出し失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ設計。
    - API 呼び出しの再試行ロジック（429/ネットワーク/タイムアウト/5xx）を備える。テスト向け差し替えを想定。

- データ基盤（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを元に営業日判定・前後営業日の取得・期間内営業日列挙等を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未取得の際は曜日ベース（平日）でフォールバックする堅牢なロジック。
    - calendar_update_job により J-Quants API から差分取得して market_calendar を冪等保存するバッチ処理を実装（バックフィル、健全性チェックを含む）。
    - 最大探索範囲を定めて無限ループを防止。

  - ETL パイプライン基盤（kabusys.data.pipeline / etl）
    - ETLResult データクラスを定義し、ETL 実行結果（取得数、保存数、品質問題、エラー等）を構造化して返却 / ログに利用可能に。
    - 差分更新・バックフィルの方針、品質チェックの取り扱い方針を実装方針として明示。
    - kabusys.data.etl から ETLResult を再エクスポート。

  - jquants_client への参照（calendar_management / pipeline）により J-Quants API との連携を想定（fetch/save 関数を利用）。

- リサーチ機能（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン、ma200 乖離）、ボラティリティ（20日 ATR、相対ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER、ROE）を DuckDB の prices_daily / raw_financials から計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None 戻し、結果を (date, code) ベースの dict リストで返却。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）: 任意ホライズン（既定 [1,5,21]）に対応。入力検証と単一クエリでの取得を実装。
    - IC 計算（calc_ic）: スピアマンのランク相関によるファクター有効性評価。少数データ / 分散ゼロの扱いを考慮。
    - ランク関数（rank）、ファクター統計サマリー（factor_summary）を実装。
  - research パッケージ __init__ で便利関数群を再エクスポート（zscore_normalize の参照含む）。

Other / Design notes
- ルックアヘッドバイアス防止:
  - 多くの関数（news/ai/regime/etl/research）は datetime.today() / date.today() を内部で参照せず、target_date を明示的に受け取る設計。
  - DB クエリは target_date 未満や排他範囲の指定などで将来データ参照を防止。
- データベース: DuckDB を主要な分析 DB として利用。書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等パターンや ROLLBACK を含む堅牢な実装。
- テスト容易性: OpenAI 呼び出しなどが差し替え可能に設計されている（ユニットテストでのモックを想定）。
- ロギング: 各処理で詳細な情報・警告を出力し、例外発生時にログを残す実装。

Fixed
- 初回リリースのため該当なし。

Changed
- 初回リリースのため該当なし。

Breaking Changes
- 初回リリースのため該当なし。

Acknowledgements / Notes
- OpenAI クライアントには gpt-4o-mini を想定。API の挙動や SDK バージョンに依存する部分はログやフェイルセーフで扱う設計です。
- 実運用では環境変数（API キー等）の管理・権限・ネットワーク設定に注意してください。