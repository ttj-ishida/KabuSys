# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。  
安定リリースや重要な変更点はここに記録します。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

---

## [0.1.0] - 2026-04-03

最初の公開リリース。以下の主要機能と設計方針を実装しています。

### 追加 (Added)
- パッケージ基盤
  - パッケージ情報の公開（kabusys.__init__）とバージョン定義: `__version__ = "0.1.0"`。

- 設定管理（kabusys.config）
  - .env ファイルまたは環境変数からの設定読み込み機能を追加。
  - プロジェクトルート自動探索（.git または pyproject.toml を基準）によりcwd非依存で .env を読み込む。
  - .env パーサ実装（コメント、export プレフィックス、クォート内エスケープ、インラインコメントの扱い等に対応）。
  - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - 環境変数保護（OS 環境変数を protected として .env.local による上書きを制御）。
  - Settings クラスを提供し、J-Quants / kabu / LINE / DB / 監視 等の設定をプロパティで取得可能に。
  - 環境変数バリデーション（KABUSYS_ENV / LOG_LEVEL 等の許容値チェック、必須キー未設定時は例外）。

- データ関連（kabusys.data）
  - マーケットカレンダー管理（calendar_management）
    - JPX カレンダーの差分取得・夜間更新ジョブ（calendar_update_job）。
    - 営業日判定ユーティリティ: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
    - market_calendar が未取得時の曜日ベースのフォールバックを実装。
    - DB 優先の挙動、最大探索上限で無限ループを防止する設計。
  - ETLパイプライン（pipeline / etl）
    - 差分取得・保存・品質チェックを考慮した ETL インターフェースを実装。
    - ETLResult データクラスを導入（取得数・保存数・品質問題・エラー一覧の保持、辞書化ユーティリティ）。
    - jquants_client を利用した idempotent な保存（ON CONFLICT 単位の運用想定）。
    - backfill やカレンダー先読み等、現実運用向けのパラメータを実装。

- AI（kabusys.ai）
  - ニュース NLU（kabusys.ai.news_nlp）
    - raw_news と news_symbols に基づき、銘柄ごとのニュースを集約して OpenAI（gpt-4o-mini, JSON mode）でセンチメントを算出。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST。UTC 変換を内部実装）と記事集約ロジック（最大記事数・文字数トリム）。
    - バッチ処理（銘柄を最大 _BATCH_SIZE=20 件単位で API 送信）、返信のバリデーション、スコアの ±1.0 クリップ。
    - API 失敗（429/ネットワーク断/タイムアウト/5xx）に対する指数バックオフリトライ、部分失敗に備えた部分置換（DELETE → INSERT）ロジック。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込み銘柄数を返す。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio の計算、マクロ記事の抽出、OpenAI 呼び出し、スコア合成、market_regime テーブルへの冪等書き込みを実装。
    - API 失敗時は macro_sentiment=0.0 でフェイルセーフに継続。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。

- リサーチ（kabusys.research）
  - ファクター計算（factor_research）
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。
    - Volatility / Liquidity: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等。
    - Value: PER（price / EPS）、ROE（raw_financials から最新財務を取得）。
    - DuckDB を用いた SQL ベースの実装、lookup 範囲や不足データ時の None の扱いなどを規定。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（calc_forward_returns: 任意ホライズンの fwd_Xd を生成）。
    - IC（Information Coefficient）計算（calc_ic: スピアマンのランク相関）。
    - ランク変換ユーティリティ（rank: 同順位は平均ランク）。
    - 統計サマリー（factor_summary: count/mean/std/min/max/median）。

- 公開再エクスポート
  - data.pipeline.ETLResult を kabusys.data.etl 経由で再エクスポート。

### 変更 (Changed)
- 設計方針・実装上の安全策を明文化
  - 全ての AI/リサーチモジュールにおいて「ルックアヘッドバイアス防止」のため datetime.today()/date.today() を直接参照しない設計を採用。
  - DuckDB に対する操作は冪等性（DELETE→INSERT など）と部分失敗時のデータ保護を意識して実装。
  - OpenAI 呼び出しは各モジュールで独立した _call_openai_api を持ち、テスト時に差し替えやすくしている（モジュール間結合を避ける）。

### 修正 (Fixed)
- .env パーサの堅牢化
  - export プレフィックス、クォート内部のバックスラッシュエスケープ、インラインコメントの検出条件などに対応し不正パースを軽減。
- OpenAI API 呼び出しの回復力向上
  - 429/接続断/タイムアウト/5xx に対する再試行ロジックとログ出力を整備。致命的な失敗は上位へ伝播せずフェイルセーフ値を使って処理継続する箇所を明確化（AI スコア算出のロバストネス向上）。
- DuckDB 操作互換性
  - executemany に空リストを渡せない DuckDB の挙動に配慮して、空チェックを行ったうえで executemany を呼ぶように修正。

### 既知の制限 (Known issues)
- OpenAI とのやり取りは gpt-4o-mini + JSON mode を前提としているが、将来的な SDK/モデル仕様変更があった場合は追加対応が必要。
- 一部の SQL バインド（配列バインド等）は DuckDB のバージョン差で挙動が異なるため、互換性を保つ実装上の工夫がなされているが、運用環境では DuckDB のバージョン確認が推奨されます。

---

開発者向けメモ:
- 主要な公開関数
  - kabusys.config.settings（Settings クラスインスタンス）
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - kabusys.data.calendar_management.calendar_update_job(conn, lookahead_days=...)
  - kabusys.data.pipeline.ETLResult（ETL 結果表現）
- 動作上の前提
  - DuckDB を利用するため、接続オブジェクト（duckdb.DuckDBPyConnection）を各関数に渡す必要があります。
  - OpenAI API キーは引数で注入可能（テスト容易化）。未指定時は環境変数 OPENAI_API_KEY を参照します。

[0.1.0]: https://example.com/release/0.1.0 (初回リリース)