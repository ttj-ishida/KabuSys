# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、互換性はセマンティックバージョニングに従います。

※このファイルはコードベースから推測して作成しています（実際のコミット履歴ではありません）。

## [0.1.0] - 2026-04-04

### 追加
- 初回リリース。日本株自動売買システム "KabuSys" のコア機能群を提供。
- パッケージメタ情報
  - バージョン: 0.1.0
  - パッケージ説明: 日本株自動売買システム
  - エクスポート: data, strategy, execution, monitoring を公開モジュールとして定義。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダを実装。読み込み順序は OS 環境変数 > .env.local > .env。
  - プロジェクトルートの自動検出: .git または pyproject.toml を探索してルートを判定（CWD に依存しない）。
  - .env パーサを実装（コメント、export プレフィックス、クォート・エスケープ、インラインコメントの扱いに対応）。
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを公開（J-Quants / kabu API / LINE / DB パス / 監視設定 / システム設定など多数のプロパティ）。
  - 必須設定の取得時に未設定であれば ValueError を送出する _require ユーティリティ。
  - KABUSYS_ENV と LOG_LEVEL の入力検証（有効値制限）および is_live / is_paper / is_dev のヘルパ。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini、JSON Mode）でセンチメントを算出して ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB を参照）。
    - バッチ処理: 最大 20 銘柄ずつ送信、1 銘柄あたり最大記事数・最大文字数でトリム（トークン肥大化対策）。
    - 再試行・バックオフ: 429/ネットワーク断/タイムアウト/5xx を対象に指数バックオフで再試行。
    - レスポンス検証: JSON 抽出、"results" リスト構造の検証、未知コードの無視、スコアを ±1.0 でクリップ。
    - DB 書き込みは冪等（対象コードの DELETE → INSERT）で、部分失敗時に既存スコアを保護する実装。
    - API キー注入可能（api_key 引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で 'bull'/'neutral'/'bear' を判定。
    - prices_daily / raw_news を参照して ma200_ratio とマクロ記事を取得し、OpenAI で macro_sentiment を算出。合成スコアは clip 後で閾値判定。
    - OpenAI 呼び出しは JSON Mode、再試行とフォールバック（API 失敗時は macro_sentiment=0.0）を実装。
    - market_regime テーブルへの書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で行う。
    - API キーは引数または OPENAI_API_KEY で指定。未指定時は ValueError を送出。

- データ基盤関連 (kabusys.data)
  - ETL パイプライン用インターフェースとデータクラス
    - pipeline.ETLResult を公開（kabusys.data.etl から再エクスポート）。
    - ETLResult は取得件数・保存件数・品質チェック結果・エラー一覧などを保持し、辞書化メソッド to_dict を提供。
  - ETL パイプライン (kabusys.data.pipeline)
    - 差分取得、バックフィルの概念、品質チェックの集約といった DataPlatform 指針に従った設計。
    - 最小データ日、バックフィル日数、カレンダー先読み等の定数を定義。
    - DuckDB 接続を前提とするユーティリティ（テーブル存在チェック、最大日付取得など）。
  - 市場カレンダー管理 (kabusys.data.calendar_management)
    - market_calendar を用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB に値がない場合は曜日ベースのフォールバック（平日は営業日）を一貫して使用。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等に更新（バックフィル・整合性チェックを実装）。
    - 最大探索範囲 (_MAX_SEARCH_DAYS) による無限ループ防止や健全性チェックの実装。

- リサーチ / ファクター群 (kabusys.research)
  - factor_research
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR 等）、Value（PER, ROE）等の定量ファクターを計算する関数を実装:
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)
    - DuckDB を用いた SQL ベースの計算。結果は (date, code) キーを持つ dict のリストで返す。データ不足時は None を返す設計。
  - feature_exploration
    - 将来リターン算出: calc_forward_returns(conn, target_date, horizons)
    - IC（Spearman）計算: calc_ic
    - ランク変換ユーティリティ: rank
    - 統計サマリー: factor_summary（count/mean/std/min/max/median）
    - pandas 等に依存しない純標準ライブラリ実装。

### 変更
- （初版のため過去変更はなし）

### 修正
- （初版のため過去修正はなし）

### 非推奨
- （初版のため該当なし）

### 削除
- （初版のため該当なし）

### セキュリティ
- OpenAI API キーやその他機密は環境変数経由で注入する設計。自動 .env ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。

### 注意事項 / 実装上の設計判断（要点）
- ルックアヘッドバイアスの回避: 日付やウィンドウ計算は datetime.today()/date.today() を直接参照せず、target_date を明示的に渡す設計。
- OpenAI 呼び出し: gpt-4o-mini の JSON Mode を使用。API エラー時はフォールバックして処理を続行（安全側の挙動）。
- DuckDB を主要なオンディスク DB として利用する前提で SQL を設計（executemany の空リスト制約等に対応）。
- DB 書き込みは可能な限り冪等にして部分失敗時のデータ保全を図る（DELETE → INSERT 等）。
- テスト容易性のため、OpenAI 呼び出し箇所やスリープ関数等は差し替え可能に実装（unittest.mock.patch を想定）。

---

今後のリリースでは「API の追加」「性能改善」「監視・実行モジュールの詳細」などを記録していきます。