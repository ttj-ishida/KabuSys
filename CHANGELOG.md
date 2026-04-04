Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

[Unreleased]: https://example.com/kabusys/compare/HEAD...v0.1.0
[0.1.0]: https://example.com/kabusys/releases/tag/v0.1.0

## [0.1.0] - 2026-04-04

Added
- パッケージ初期リリース。モジュール群と主要機能を実装。
  - kabusys パッケージのバージョン: 0.1.0（src/kabusys/__init__.py）
  - 公開サブパッケージ: data, strategy, execution, monitoring

- 環境変数 / 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込み。
  - 自動読み込みはプロジェクトルート（.git または pyproject.toml）起点で探索し、CWD に依存しない実装。
  - 読み込み優先順: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント（スペース直前の # をコメントとみなす）に対応。
  - 上書き制御（override）や OS 環境変数の保護（protected set）に対応。
  - Settings クラスを提供（J-Quants / kabu API / LINE / DB パス / 監視設定 / システム設定等のプロパティ）。
  - KABUSYS_ENV / LOG_LEVEL のバリデーション、is_live/is_paper/is_dev ヘルパーあり。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を基に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を使ってセンチメントを取得。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB と比較）。
    - バッチ処理（最大 20 銘柄 / チャンク）、各銘柄は最大 10 記事・最大 3000 文字でトリム。
    - リトライ戦略（429, ネットワーク断, タイムアウト, 5xx）: 指数バックオフ。
    - レスポンスのバリデーション（JSON 抽出、"results" 構造、コード整合性、数値チェック）、スコアは ±1.0 にクリップ。
    - 書き込みは部分置換（対象コードのみ DELETE → INSERT）して部分失敗時に既存データを保護。
    - テスト容易性のため OpenAI 呼び出し関数を差し替え可能（ユニットテスト用に patch しやすい構成）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し、日次で market_regime テーブルへ冪等書き込み。
    - マクロニュースは news_nlp のウィンドウ計算を利用してフィルタ（マクロキーワード群）し、OpenAI（gpt-4o-mini, JSON Mode）で macro_sentiment を取得。
    - レジームスコア合成とラベリング（bull/neutral/bear）を実装。API エラー時は macro_sentiment=0.0 とするフェイルセーフ。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT で冪等性を保つ。エラー時は ROLLBACK を試行し、失敗ログを出力。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー管理ロジック: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - market_calendar が未取得の場合は曜日ベースのフォールバック（平日＝営業日）を行い、一貫した振る舞いを保証。
    - 最大探索範囲制限（_MAX_SEARCH_DAYS）や先読み／バックフィルロジック、健全性チェックを実装。
    - 夜間バッチ job (calendar_update_job) を実装し、J-Quants クライアント経由で差分取得→保存（保存は jquants_client 側に委譲）。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを実装（取得数・保存数・品質問題・エラー 等を集約）。
    - 差分更新、バックフィル、品質チェック（quality モジュールとの連携）、idempotent な保存方針を想定した設計。
    - pipeline のインターフェース（ETLResult）を etl モジュールで再公開。

- 研究（research）モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。必要行数未満は None を扱う。
    - calc_value: raw_financials から最新の財務データを取得して PER / ROE を計算（EPS が 0/欠損なら PER = None）。
    - いずれの関数も DuckDB 接続を受け取り SQL ベースで処理し、(date, code) ベースの辞書リストを返す。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを計算。ホライズンは検証済みの整数範囲制約あり。
    - calc_ic: factor と将来リターンのスピアマン（ランク相関）を計算。有効レコード 3 件未満で None を返す。
    - rank: 同順位は平均ランクを返す実装（丸め対策あり）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー機能。
    - kabusys.data.stats.zscore_normalize を再エクスポート。

- 実装方針・品質面の配慮
  - DuckDB を主要なローカル DB として利用（SQL とウィンドウ関数を活用）。
  - ルックアヘッドバイアス防止: datetime.today()/date.today() を直接参照しない設計（target_date ベースで計算）。
  - API 呼び出しはフェイルセーフ（LLM の失敗や API エラー時にはスコアを 0 にフォールバック／スキップして処理継続）。
  - ロギング（info/warning/debug）を多用して実行状況と問題点を可視化。
  - テスト容易性: OpenAI 呼び出し部分など差し替え可能な構造にしている（ユニットテストでの patch を想定）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 該当なし。

Removed
- 該当なし。

Security
- 該当なし。API キーは環境変数から取得することを想定（OpenAI API キーの指定がない場合は ValueError を投げる設計）。

注意事項（ユーザー向け）
- OpenAI 利用
  - news_nlp / regime_detector / score_news / score_regime は OpenAI API（gpt-4o-mini）を利用します。api_key を引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
  - API の安定性に依存するため、レート制限やネットワーク断に対するリトライ処理はあるものの、料金・利用制約には注意してください。
- 環境変数自動ロード
  - プロジェクトルート判定はパッケージ内の __file__ を起点に行います。配布後の実行環境でも期待どおりに動作する設計ですが、必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を使用して自動読み込みを無効化できます。
- DB 互換性
  - DuckDB のバージョン差で executemany の空リストバインドなど挙動差があるため、一部実装は互換性確保のための回避策を採用しています。

今後の予定（一例）
- PBR や配当利回りなどのバリューファクター追加。
- 発注ロジック（execution）および監視（monitoring）モジュールの拡充。
- テストカバレッジの強化と CI ワークフロー整備。

---
この CHANGELOG はコードベース（src/ 以下）の実装内容から推測して作成しています。実際のリリースノートやユーザー向けのドキュメントは必要に応じて補足・修正してください。