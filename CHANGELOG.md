Changelog
=========

すべての重要な変更点を記録します。  
このファイルは Keep a Changelog のフォーマットに準拠しています。  
セマンティックバージョニングを用います。  

[Unreleased]
------------

（現在差分はありません）

[0.1.0] - 2026-03-31
-------------------

Added
- 初回公開: kabusys パッケージ（日本株自動売買／データ基盤／調査用ユーティリティ群）。
- パッケージ初期情報:
  - バージョン: 0.1.0
  - パッケージの公開モジュール: data, strategy, execution, monitoring（パッケージ公開設定）。
- 環境設定管理 (kabusys.config):
  - プロジェクトルート検出: 現在ファイル位置から .git または pyproject.toml を探索してプロジェクトルートを自動判定。
  - .env 自動読み込み: OS 環境変数 > .env.local > .env の優先順位で自動ロード（テスト等で KABUSYS_DISABLE_AUTO_ENV_LOAD を使用して無効化可）。
  - .env パーサー強化: export プレフィックス対応、シングル/ダブルクォートとバックスラッシュエスケープ処理、インラインコメントの扱い、無効行スキップ等に対応。
  - 保護機能: OS の既存環境変数を保護して .env による上書きを制御。
  - Settings クラス: J-Quants / kabuAPI / Slack / DB パス / 監視閾値 / 環境 (development/paper_trading/live) / ログレベル 等のプロパティを提供し、必須値未設定時は明示的にエラーを発生させる。
- AI モジュール (kabusys.ai):
  - news_nlp.score_news:
    - ニュース集約ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST 相当の UTC 範囲）。
    - raw_news と news_symbols を結合して銘柄毎に最新記事を集約（記事数・文字数上限でトリミング）。
    - OpenAI（gpt-4o-mini）の JSON モードを用いたバッチ評価（銘柄ごとに最大バッチサイズを設定）と、429/ネットワーク/タイムアウト/5xx に対するエクスポネンシャルバックオフによるリトライ。
    - レスポンスの厳密バリデーション（JSONパース、results 配列、code と score の検証、スコアのクリップ）。
    - 成功スコアのみを ai_scores テーブルに冪等的に置換（DELETE → INSERT）し、部分失敗時に既存データを保護。
    - ルックアヘッドバイアス防止: datetime.today()/date.today() を参照せず、target_date を明示的に使用。
  - regime_detector.score_regime:
    - ETF (1321) の 200 日移動平均乖離 (ma200_ratio) とマクロニュースの LLM センチメントを合成して日次の市場レジームを判定（重み: MA70% / Macro30%）。
    - マクロ記事はキーワードフィルタで抽出、LLM 呼び出しは失敗時にフェイルセーフ（macro_sentiment=0.0）。
    - OpenAI 呼び出しは独立実装で、JSON レスポンス処理とリトライを備える。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
- 研究モジュール (kabusys.research):
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日MA乖離（データ不足時は None）を DuckDB の SQL で計算。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を制御して正確に集計。
    - calc_value: raw_financials の直近財務（report_date <= target_date）と株価を組み合わせて PER／ROE を算出（EPS 0/欠損は None）。
    - 全て関数は DuckDB 接続を受け取り、prices_daily / raw_financials のみ参照（発注等の副作用なし）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD を用いて一度のクエリで取得。horizons の妥当性チェックあり。
    - calc_ic: Spearman ランク相関（Information Coefficient）を実装。データ不足（有効レコード < 3）時は None を返す。
    - rank: 同順位は平均ランク扱い（丸めによる ties 検出漏れを防ぐため round を使用）。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで算出。
- データ基盤モジュール (kabusys.data):
  - calendar_management:
    - JPX カレンダー管理機能（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB に calendar データがある場合は DB 優先、未登録日は曜日ベースのフォールバック（週末除外）を使用。最大探索日数で無限ループを防止。
    - calendar_update_job: J-Quants API から差分フェッチし market_calendar を冪等保存。バックフィルと健全性チェックを実装。
  - pipeline / ETL:
    - ETLResult dataclass を公開（ターゲット日、取得/保存件数、品質問題、エラー等を保持）。to_dict(), has_errors, has_quality_errors を提供。
    - ETL パイプライン設計に沿った差分取得・保存・品質チェックのための基礎実装（jquants_client / quality モジュールと連携する想定）。
  - etl の公開インターフェース (kabusys.data.etl) で ETLResult を再エクスポート。
- パッケージ公開の補助:
  - 各サブパッケージの __init__ ファイルで主要 API を __all__ として整理して公開。

Security / Reliability / Design
- すべての「日付基準」処理は target_date ベースで実装し、内部で datetime.today()/date.today() を参照しない設計（ルックアヘッドバイアス防止）。
- 外部 API 呼び出し（OpenAI / J-Quants）は堅牢化（リトライ、バックオフ、失敗時のフォールバック）を行い、致命的障害を発生させない方針を採用（部分失敗はスキップして継続）。
- DuckDB に対する互換性考慮:
  - executemany に空リストを渡さないチェック（DuckDB 0.10 の制約回避）。
  - SQL 側で ROW_NUMBER / WINDOW を活用して最新レコードやリードラグを取得。
- ロギングと警告を多用し、異常検知やデバッグを容易にする設計。

Notes / Known limitations
- OpenAI の呼び出しは gpt-4o-mini（JSON モード）を想定。API の SDK 変更に対して一部互換性防衛コード（status_code の安全取得等）を実装していますが、将来的な SDK の大きな変更は追加対応が必要になる場合があります。
- 一部モジュール（例: jquants_client / quality / strategy / execution / monitoring の詳細実装）はこのリリースでは外部モジュールとして連携することを想定しています（stub/依存として扱う必要あり）。
- ETL パイプラインの一部実装（ファイル末尾の未完部など）は拡張・補完の余地があります（次期リリースでの改善対象）。

ライセンス、貢献、連絡先などはリポジトリの README 等を参照してください。