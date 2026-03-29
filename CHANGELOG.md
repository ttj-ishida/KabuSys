CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
リリース日付はソースコードの作成時点を元に推測して記載しています。

Unreleased
----------

（現時点の開発中の変更はここに記載してください）

0.1.0 - 2026-03-29
------------------

Added
- パッケージ初回リリース: kabusys (バージョン 0.1.0)
  - パッケージメタ: src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ として公開。

- 環境設定/ローダ
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする機能を追加（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理等に対応）。
  - _load_env_file による保護キー（OS 環境変数の保護）と override 挙動を実装。
  - Settings クラスを実装し、環境変数からアプリ設定を安全に取得（必須キーチェックを行い未設定時は ValueError を送出）。
  - 主要設定プロパティ（J-Quants, kabuステーション, Slack, DB パス, env/log_level 判定、is_live/is_paper/is_dev）を提供。デフォルト値やバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値）を実装。

- AI（自然言語処理）モジュール
  - news_nlp モジュールを追加（kabusys.ai.news_nlp）。
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini, JSON Mode）でセンチメントを取得。
    - 時間ウィンドウ計算（前日15:00 JST ～ 当日08:30 JST を UTC に変換）を calc_news_window で提供。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄/回）、記事数/文字数トリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - 再試行ロジック（429/ネットワーク/タイムアウト/5xx を指数バックオフでリトライ）、レスポンス検証（JSON 抽出・構造チェック・数値検証）、スコアの ±1.0 クリップ。
    - DuckDB への書き込みは部分置換（DELETE → INSERT）を行い、部分失敗時に他銘柄データを保護。
    - テスト容易性のため _call_openai_api をモック差し替え可能に実装。

  - regime_detector モジュールを追加（kabusys.ai.regime_detector）。
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio の計算（target_date 未満のデータのみを使用しルックアヘッドを防止）、マクロ記事抽出（キーワードによるフィルタ）、OpenAI 呼び出し（gpt-4o-mini）による macro_sentiment 評価を実装。
    - API 呼び出し失敗時は macro_sentiment を 0.0 にフォールバック（フェイルセーフ）。OpenAI 呼び出し部分もテストで差し替え可能。
    - レジームスコア合成、閾値に基づくラベル付与、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - API リトライ／エラー処理（RateLimit, 接続エラー, タイムアウト, APIError の 5xx ハンドリング）を備える。

- Data（データ基盤）モジュール
  - calendar_management を追加（kabusys.data.calendar_management）。
    - JPX カレンダーの夜間バッチ更新ロジック（calendar_update_job）と市場カレンダーの CRUD/判定ユーティリティを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の一貫した営業日判定 API を提供。
    - market_calendar が未取得の場合は曜日（土日）ベースのフォールバックを採用。DB 登録値を優先する設計。
    - 最大探索日数制限（_MAX_SEARCH_DAYS）やバックフィル日数、健全性チェック（将来日付の異常検出）を実装。

  - ETL パイプラインとユーティリティを追加（kabusys.data.pipeline, kabusys.data.etl）。
    - ETLResult データクラスを実装し、ETL 実行結果（取得数・保存数・品質問題・エラー等）を集約できるようにした。
    - 差分取得、バックフィル、品質チェック（quality モジュール連携）を想定した設計。J-Quants クライアント（jquants_client）経由での取得・保存を想定。
    - 内部ヘルパー：テーブル存在チェック、最大日付取得、トレーディング日調整などを実装。
    - kabusys.data.etl で pipeline.ETLResult を再エクスポート。

- Research（リサーチ）モジュール
  - ファクター計算: calc_momentum / calc_volatility / calc_value を実装（kabusys.research.factor_research）。
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）。
    - Volatility: 20 日 ATR、ATR 比率、平均売買代金、出来高比率。
    - Value: raw_financials からの EPS/ROE を使った PER / ROE 計算（最新レポートデータを target_date 以前から取得）。
    - すべて DuckDB の prices_daily / raw_financials をベースに計算（外部 API 不使用）。
  - 特徴量探索: calc_forward_returns / calc_ic / factor_summary / rank を実装（kabusys.research.feature_exploration）。
    - 将来リターン calc_forward_returns は複数ホライズンに対応、最大ホライズンの 2 倍カレンダー日でスキャン範囲を限定。
    - IC（Spearman の ρ）計算を実装（ランク化、同順位は平均ランク処理、データ不足時は None）。
    - factor_summary により count/mean/std/min/max/median を算出。
    - rank ユーティリティは丸め誤差対策（round 12 桁）を行う。

- その他ユーティリティ
  - kabusys.ai.__init__ と kabusys.research.__init__ などで適切なシンボルを公開。
  - テスト用に内部 API 呼び出しの差し替えポイント（_call_openai_api の patch）を用意。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （該当なし）

注記（実装上の重要ポイント、運用上の注意）
- OpenAI API キーは各関数の引数で注入可能。未指定時は環境変数 OPENAI_API_KEY を参照し、未設定だと ValueError を送出するため運用時は必ず設定が必要。
- .env 自動読み込みはプロジェクトルート検出に依存する（.git または pyproject.toml）。配布後や特殊な実行環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用すること。
- DuckDB への executemany に空リストを渡すと失敗する点に配慮し、空チェックを行ってから実行している（互換性確保）。
- 時刻・日付は原則 timezone を混入させず date / naive datetime を使用する設計。ニュースのウィンドウ計算は JST を基準に UTC naive datetime を返す。
- LLM 呼び出しのフェイルセーフ: 一時エラーやパースエラーが起きてもシステム全体を停止させないよう、デフォルト値やスキップ動作で継続できる設計になっている。

今後の予定（例）
- strategy / execution / monitoring の具体実装（現時点では名前空間のみ公開）。
- スコアリングや ETL の性能改善、より詳細な品質チェックルールの追加。
- テストの充実（外部 API モックによる統合テスト含む）。

--- 

この CHANGELOG はコード内容からの推測に基づいて作成しています。実際のリリースノート作成時は変更履歴管理（git の履歴等）を基に調整してください。