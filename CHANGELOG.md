# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。  
このプロジェクトはセマンティックバージョニング（SemVer）を採用しています。

## [Unreleased]

## [0.1.0] - 2026-04-03
### Added
- 初回リリース。日本株自動売買システム「KabuSys」の基本モジュール群を実装。
- パッケージメタ情報
  - バージョン: 0.1.0（src/kabusys/__init__.py）。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ で定義。

- 環境設定 / ローディング（src/kabusys/config.py）
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
  - プロジェクトルート検出: __file__ を起点に .git または pyproject.toml を探索して自動ロード。
  - .env パーサ: export プレフィックス対応、シングル／ダブルクォートのエスケープ処理、インラインコメント処理等に対応する堅牢なパース実装。
  - .env 自動読み込みの優先順: OS環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - 上書き保護: OS環境変数を protected として .env からの上書きを制御。
  - Settings クラス: 各種必須／任意設定（J-Quants、kabuステーション、LINE、DBパス、監視閾値等）をプロパティで公開。KABUSYS_ENV / LOG_LEVEL の値検証を実施。
  - 必須環境変数未設定時は明示的に ValueError を送出。

- ニュースNLP（src/kabusys/ai/news_nlp.py）
  - raw_news / news_symbols を基に銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でセンチメントを取得して ai_scores テーブルへ書き込む機能を実装。
  - タイムウィンドウ定義（JST 前日15:00 ～ 当日08:30 -> UTC に変換）と calc_news_window ユーティリティを提供。
  - バッチ処理（最大20銘柄／チャンク）・銘柄内記事トリム（最大記事数、最大文字数）によるトークン爆発対策。
  - JSON Mode を利用した厳格なレスポンス検証と復元ロジック（余分な前後テキストから最外の {} を抽出する処理含む）。
  - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフのリトライ実装。失敗時は該当チャンクをスキップして処理継続（フェイルセーフ）。
  - スコアは ±1.0 にクリップ。部分書き換え（DELETE → INSERT）を行い、部分失敗時に既存スコアを保護。
  - テスト容易性: _call_openai_api をモック差し替え可能に設計。

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321（日経225連動）の 200 日移動平均乖離（重み70%）と、マクロ経済ニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルに冪等書き込みする機能を実装。
  - マクロ記事の抽出（キーワードベース）・OpenAI 呼び出し（gpt-4o-mini）・JSON パース・リトライ/フォールバックロジックを備える。API失敗時は macro_sentiment=0.0 として継続。
  - ルックアヘッドバイアス回避の設計（target_date 未満のデータのみ利用、datetime.today() を参照しない等）。
  - テスト容易性: news_nlp と結合せず独立した _call_openai_api 実装によりモジュール結合を抑制。

- データパイプライン / ETL（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
  - ETLResult データクラスを公開（ETL の取得件数、保存件数、品質問題、エラー等を集計可能）。
  - 差分更新・バックフィル・品質チェックの設計方針を実装。J-Quants クライアント経由で差分取得し idempotent に保存する想定。
  - DuckDB を前提としたテーブル存在チェックや最大日付取得のユーティリティを実装（互換性と安全性に配慮）。

- カレンダー管理（src/kabusys/data/calendar_management.py）
  - market_calendar を基に営業日判定・翌営業日／前営業日取得・期間内営業日取得・SQ日判定機能を実装。
  - DB 未取得時の曜日ベースフォールバック、DB 優先ルール、最大探索日数制限、健全性チェック等を実装。
  - calendar_update_job: J-Quants から差分取得して market_calendar に冪等保存する夜間バッチ処理を実装（バックフィルと健全性チェック含む）。
  - jquants_client と連携する想定（fetch / save の呼び出し箇所を準備）。

- リサーチ / ファクター計算（src/kabusys/research/*）
  - ファクター計算モジュールを実装:
    - calc_momentum: 1M/3M/6M リターン、200日MA乖離を計算（データ不足時は None）。
    - calc_volatility: 20日ATR、相対ATR、20日平均売買代金、出来高比率を計算（データ不足時は None）。
    - calc_value: raw_financials と当日の株価から PER、ROE を計算（EPS=0や欠損は None）。
  - 特徴量探索モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: factor と将来リターンのスピアマンランク相関（IC）を計算。十分なデータが無ければ None。
    - factor_summary: 基本統計量（count, mean, std, min, max, median）を計算。
    - rank: 同順位は平均ランクで処理するランク化ユーティリティを実装。
  - DuckDB 上の SQL ウィンドウ関数を活用し高速に集計する設計。外部ライブラリへの依存を避け、標準ライブラリのみで実装。

- ロギング / トランザクション / エラーハンドリング
  - 各所で BEGIN / DELETE / INSERT / COMMIT を用いた冪等書き込みを採用。例外時は ROLLBACK を試行し、ROLLBACK 自体の失敗は警告ログ化。
  - API呼び出し・DB操作失敗時はフェイルセーフ（例: スコア算出が失敗しても全体停止せず部分スキップ）を基本方針として実装。
  - 詳細な logger.info / logger.warning / logger.exception により運用時の監査性を確保。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Deprecated
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security
- OpenAI / J-Quants / kabu ステーション等の API キーは環境変数で管理する設計。コード中に API キーは含まれない。必須キー未設定時は明示的エラーを出す実装。
- .env の読み込みはデフォルトで自動だが、テストや安全性のため KABUSYS_DISABLE_AUTO_ENV_LOAD により明示的に無効化可能。

---

注: 本 CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノートには追加の運用情報や既知の制約（互換性、既知のバグ、外部APIの利用制限など）を追記することを推奨します。