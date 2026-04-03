Changelog
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」（https://keepachangelog.com/ja/1.0.0/）に準拠します。

Unreleased
----------

（現在未リリースの変更はここに記載します）

[0.1.0] - 2026-04-03
-------------------

初回公開リリース。以下の主要機能・モジュールを実装しています。

Added
- パッケージ基礎
  - パッケージ名: kabusys、__version__ を "0.1.0" として定義。
  - パッケージ公開 API: data, strategy, execution, monitoring のトップレベルエクスポート（__all__）。
- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env パーサを実装: コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いをサポート。
  - 自動読み込みの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを追加し、アプリ設定（J-Quants トークン、kabu API, LINE, DB パス、監視閾値、環境・ログレベル検証等）をプロパティ経由で取得可能に。
  - 必須環境変数未設定時は ValueError を投げる _require 実装。
  - 環境値の検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）を実装。
- データ基盤（kabusys.data）
  - ETL やカレンダー管理などの基盤モジュールを実装。
  - pipeline.ETLResult データクラス（ETL 実行の概要・品質問題・エラーを格納、辞書化メソッドを提供）を公開。
  - etl モジュールは pipeline.ETLResult を再エクスポート。
- カレンダー管理（kabusys.data.calendar_management）
  - JPX カレンダーを扱う market_calendar テーブル向けユーティリティを実装（営業日判定、次/前営業日、期間内営業日取得、SQ判定）。
  - market_calendar が未登録の場合は曜日ベース（土日除く）でフォールバックするロジック。
  - 夜間バッチ calendar_update_job 実装（J-Quants から差分取得、バックフィル、健全性チェック、冪等保存を想定）。
  - DB 存在チェック・NULL 値への耐性・最大探索日数による無限ループ防止等の安全策を実装。
- ETL パイプライン（kabusys.data.pipeline）
  - ETL の設計方針に沿ったユーティリティ群（差分取得、保存、品質チェックのフックを想定）。
  - DuckDB のテーブル存在チェックや最大日付取得ユーティリティを実装。
  - ETLResult による処理結果集約と品質エラー判定ロジックを提供。
- 研究用 / ファクター計算（kabusys.research）
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離などモメンタム系ファクターを計算。
    - calc_volatility: 20日 ATR、相対ATR、平均売買代金、出来高比率などのボラティリティ/流動性指標を計算。
    - calc_value: EPS/ROE を用いた PER / ROE 計算（raw_financials と prices_daily から取得）。
    - 各関数は DuckDB の SQL を活用し、欠損／データ不足時には None を返すポリシー。
  - feature_exploration モジュール:
    - calc_forward_returns: 将来リターン（複数ホライズン）を LEAD を用いて一括計算。horizons 引数の検証を実施。
    - calc_ic: スピアマンのランク相関（IC）を実装。データ不足時は None を返す。
    - rank: 同順位は平均ランクとするランク化ユーティリティ（丸めで ties の検出漏れを防止）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー機能。
  - 研究API を __init__ でまとめてエクスポート（calc_momentum 等）。
- AI / ニュース NLP（kabusys.ai）
  - news_nlp モジュール:
    - score_news: raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini の JSON Mode）へバッチ送信して銘柄ごとのセンチメント ai_score を ai_scores テーブルへ保存。
    - ニュースの時間ウィンドウ計算 (JST ベース → UTC に変換) を実装（calc_news_window）。
    - バッチサイズ、記事／文字数トリム、リトライ（429/ネットワーク/5xx）と指数バックオフ、レスポンスの堅牢なバリデーションを実装。
    - API 失敗時は個別チャンクをスキップし、フェイルセーフで処理継続する設計。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能（_call_openai_api が patch 可能）。
  - regime_detector モジュール:
    - ETF 1321（Nikkei 225 連動 ETF）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出（キーワードベース）、OpenAI への再試行ロジック、レスポンス JSON の堅牢なパースを備える。
    - LLM API 失敗時のフォールバック（macro_sentiment=0.0）を実装し、例外を広げないフェイルセーフ設計。
    - テスト向けに _call_openai_api を差し替え可能。
- ロギングとトランザクション
  - 各所で BEGIN / DELETE / INSERT / COMMIT といった冪等更新、例外時の ROLLBACK とログ出力を実装して安全に DB 書き込みを行う。
  - 多くの箇所で詳細な logger.info / logger.warning / logger.debug を出力するよう設計。

Changed
- 新規リリースのため該当なし。

Fixed
- 新規リリースのため該当なし。

Deprecated
- なし。

Removed
- なし。

Security
- OpenAI API キー取得は明示的に api_key 引数または環境変数 OPENAI_API_KEY を要求。未設定時は ValueError を発生させる（安全策）。

Notes / 設計上の留意点
- ルックアヘッドバイアス対策として、各種処理（score_news, score_regime, calc_*）は内部で datetime.today()/date.today() を直接参照しない設計。必ず target_date を明示的に渡すことを想定。
- DuckDB をデータストアとして前提とした SQL 中心の実装。DuckDB バージョン差異（executemany の空リスト制約など）に配慮した実装がされている。
- テスト容易性を考え、外部 API 呼び出し箇所は patch できるよう設計ドキュメントやコメントを付与。
- J-Quants 連携箇所は jquants_client を参照（実装は別モジュール想定）。

作成者注
- 上記変更履歴はリポジトリ内の現行ソース内容から推測してまとめた初期リリースノートです。実際のリリース履歴や過去のバージョン差分がある場合はそれに合わせて追記・修正してください。