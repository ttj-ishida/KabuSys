CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従い、セマンティックバージョニング (semver) を採用しています。

Unreleased
----------
（現在未リリースの変更はここに記載します）

0.1.0 - 2026-04-03
-----------------

初回公開リリース。KabuSys のコア機能群を実装しました。主にデータ取り込み（ETL）、マーケットカレンダー管理、ファクター／リサーチ機能、およびニュース・マクロの AI スコアリングを提供します。

Added
- パッケージ基盤
  - 初期パッケージ公開 (kabusys) とサブモジュール公開設定を追加（src/kabusys/__init__.py）。
  - public API: data, strategy, execution, monitoring を __all__ に定義。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは OS 環境変数からの設定読み込みを自動化（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env パーサ実装：export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応（kabusys/config.py）。
  - 自動読み込み無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
  - 必須変数チェック (_require) と Settings クラスを実装。主要設定項目（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、LINE 関連、DB パス、監視閾値、環境/ログレベル検証など）をプロパティで提供。

- データプラットフォーム / ETL（kabusys.data.pipeline, kabusys.data.etl）
  - ETLResult データクラスを実装し、ETL 実行結果（取得数、保存数、品質問題、エラー等）を標準化（kabusys/data/pipeline.py, kabusys/data/etl.py）。
  - 差分取得、backfill、品質チェックを想定した ETL の設計方針をドキュメント化。

- カレンダー管理（kabusys.data.calendar_management）
  - JPX マーケットカレンダー取得/保存のための夜間バッチジョブ（calendar_update_job）実装。
  - 営業日判定・前後営業日取得・期間内営業日列挙・SQ 判定等のユーティリティを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
  - DB 未登録日の曜日ベースフォールバック、バックフィル、最大探索日数や健全性チェックの導入により堅牢性を確保。

- AI ベースのニュース / レジーム判定（kabusys.ai.news_nlp, kabusys.ai.regime_detector）
  - ニュース NLP: raw_news / news_symbols から銘柄別に記事を集約し OpenAI（gpt-4o-mini、JSON Mode）でセンチメントを算出、ai_scores テーブルへ保存する score_news を実装。
    - バッチ（_BATCH_SIZE=20）単位での API 呼び出し、記事トリム（最大記事数／文字数）、JSON レスポンスのバリデーション、スコアのクリッピング、部分書き換えによる冪等保存を実装。
    - API エラー（429/ネットワーク/タイムアウト/5xx）に対する指数バックオフリトライを実装。
    - タイムウィンドウは JST ベースで計算（前日 15:00 JST 〜 当日 08:30 JST）し、ルックアヘッドを防止。
  - 市場レジーム判定: ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で market_regime を書き込む score_regime を実装。
    - MA 計算は target_date 未満のデータのみを使用（ルックアヘッド防止）。
    - OpenAI 呼び出し失敗時は macro_sentiment を 0.0 にフォールバックするフェイルセーフを採用。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。

- リサーチ / ファクター（kabusys.research）
  - ファクター計算モジュールを実装（calc_momentum, calc_value, calc_volatility）。
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。
    - Volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率。
    - Value: raw_financials から EPS/ROE を参照して PER/ROE を算出（PBR 等は未実装）。
  - 特徴量探索モジュールを実装（calc_forward_returns, calc_ic, factor_summary, rank）。
    - 将来リターン計算は複数ホライズンに対応（デフォルト [1,5,21]）、ホライズン入力検証あり。
    - IC（Spearman ρ）計算はランク変換を行い、少数データ時の扱いを明示。
    - 統計サマリー（count/mean/std/min/max/median）を提供。
  - データ処理は DuckDB の SQL と標準ライブラリのみで完結する設計。

- DuckDB / DB 安全性対応
  - DuckDB の executemany の空リスト制約に配慮した実装（空の際は実行をスキップ）を採用。
  - 日付取り扱いはすべて datetime.date を使用し timezone 混入を防止。

Changed
- （初回リリースのため該当なし）

Fixed
- OpenAI レスポンスパースの堅牢化
  - JSON Mode でも前後に余計なテキストが混ざる場合に最外の {} を抽出して復元するロジックを追加（kabusys/ai/news_nlp.py）。
  - レスポンス構造のバリデーションを厳格化し、不正レスポンスは該当チャンク/銘柄のみスキップするように変更。
- API エラー処理
  - APIError をステータスコードに応じて 5xx はリトライ、非 5xx は即スキップするよう制御（kabusys/ai/*）。
  - リトライ時にログ出力とエクスポネンシャルバックオフを適用。
- データ不足時のフォールバック
  - MA 計算／ATR 等で必要日数に満たない場合に None または中立値（ma200_ratio=1.0 / macro_sentiment=0.0）を返すフェイルセーフを実装。
- calendar_update_job
  - market_calendar の last_date が極端に未来（健全性閾値）であれば更新をスキップして警告するチェックを追加。

Security
- 環境変数の取り扱い
  - 必須の API キー未設定時は明確な ValueError を送出（OpenAI/API/各種トークン）。
  - .env の読み込みはデフォルトで行うが無効化フラグを提供（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
  - 環境変数の保護（.env 上書き時に OS 環境変数を protected として扱う）を実装。

Notes / Design Decisions
- すべての処理で「ルックアヘッドバイアス」を防ぐ設計を優先（datetime.today() や date.today() を内部参照しない）。
- 外部 API（発注系・本番口座）にはこのリリースで一切アクセスしない設計（データ取得・解析・研究に限定）。
- DuckDB を中心に SQL と標準ライブラリで完結する実装を目指し、外部依存（pandas 等）を排除。
- OpenAI 呼び出し部分はテスト容易性のため差し替え可能（ユニットテスト向けに _call_openai_api を patch してモック化可能）。

その他
- ロギングを多用し処理状況やフェイルセーフの挙動を明示的に記録。
- 今後のリリースで予定している項目：
  - strategy / execution / monitoring モジュールの実装（注文ロジック・実行・プロセス監視）
  - PBR・配当利回りなどバリューファクターの拡張
  - ai モデル選択・プロンプトチューニング、スコアの学習ベース補正

署名
- 初回リリース (0.1.0) — KabuSys 開発チーム（ソースコードより推測）

---