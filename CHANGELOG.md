# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
このプロジェクトの初期リリース（0.1.0）は以下の内容を含みます。

## [0.1.0] - 2026-04-03
### 追加
- 基本パッケージ構成を追加
  - パッケージエントリポイント: kabusys.__version__ = 0.1.0、公開サブパッケージ: data, strategy, execution, monitoring。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルおよび環境変数から設定を自動読み込み（優先順: OS 環境 > .env.local > .env）。
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD`。
  - `.env` パーサ実装: コメント、export プレフィックス、シングル/ダブルクォート、エスケープに対応。
  - `Settings` クラスでアプリケーション設定をプロパティとして提供（J-Quants / kabuAPI / LINE / DB パス / 監視設定 / システム設定など）。
  - 必須設定未提供時は ValueError を発生。
  - env および log level の値検証（許容値チェック）。
  - Path 型プロパティは expanduser() を適用。

- AI モジュール（自然言語処理）
  - `kabusys.ai.news_nlp`
    - ニュース記事を銘柄ごとに集約して OpenAI（gpt-4o-mini）でセンチメント評価を行い、`ai_scores` テーブルへ保存する機能を実装。
    - 対象時間ウィンドウ（JST 前日 15:00 〜 当日 08:30）を UTC に変換して DB を参照するロジックを実装。
    - バッチ処理（最大 20 銘柄 / API コール）、各銘柄のトリム（最大記事数、最大文字数）によりトークン肥大を抑制。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライを実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 構造、コード整合性、数値チェック）を実装。
    - DuckDB への書き込みは冪等性（DELETE → INSERT）で実施し、部分失敗時に既存スコアを保護する設計。
    - テスト用に OpenAI 呼び出しを差し替え可能な設計（内部 _call_openai_api のパッチ可）。

  - `kabusys.ai.regime_detector`
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - マクロニュースのフィルタリング（キーワード定義）・LLM 評価（gpt-4o-mini、JSON モード）・スコア合成・閾値判定を実装。
    - API エラー時は macro_sentiment を 0.0 にフォールバックするフェイルセーフ設計。
    - 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT、エラー時は ROLLBACK）で実施。
    - テスト容易性のため OpenAI 呼び出しの差し替えを想定。

- データ処理（Data Platform）
  - `kabusys.data.calendar_management`
    - JPX マーケットカレンダー管理（market_calendar）の参照・更新・夜間バッチ（calendar_update_job）を実装。
    - 営業日判定ユーティリティ: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
    - DB 未登録日のフォールバック（曜日ベースで土日休場）や、データがまばらな場合でも一貫した判定を返す設計。
    - next/prev 検索には安全上の上限（_MAX_SEARCH_DAYS）を設け、無限ループを回避。
    - calendar_update_job は J-Quants クライアント経由で差分取得・バックフィル（直近 _BACKFILL_DAYS を再取得）・保存を行い、健全性チェック（極端に将来の日付はスキップ）を実装。

  - `kabusys.data.pipeline` / `kabusys.data.etl`
    - ETL パイプライン概念を導入（差分更新、保存、品質チェックのフロー）。
    - `ETLResult` データクラスを公開し、取得数・保存数・品質問題・エラー一覧等の結果を保持、辞書変換メソッドを提供。
    - jquants_client および quality モジュールとの連携を想定した設計（idempotent 保存、品質チェック結果を収集して呼び出し元が判断）。
    - `kabusys.data.etl` で `ETLResult` を再エクスポート。

- リサーチ / ファクター計算
  - `kabusys.research.factor_research`
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER, ROE）等のファクター計算関数を実装。
    - DuckDB に対する SQL ベースの計算を行い、外部 API には依存しない設計。
    - 各関数は (date, code) ベースの辞書リストを返す仕様。

  - `kabusys.research.feature_exploration`
    - 将来リターン計算（calc_forward_returns: デフォルト horizons = [1,5,21]、horizons の検証含む）。
    - IC（calc_ic: スピアマンのランク相関）計算、rank（同順位は平均ランクで処理）、factor_summary（基本統計量）などの解析ユーティリティを実装。
    - pandas 等に依存せず標準ライブラリ + DuckDB で完結する実装。

- テスト・運用を意識した実装上の配慮
  - 現実環境での誤用を防ぐため、すべての日付ロジックは date/ datetime を直接参照せず、外部から target_date を受け取る形でルックアヘッドバイアスを回避。
  - OpenAI 呼び出しを内部関数として分離し、ユニットテストでの差し替えを容易化。
  - DB 書き込みは可能な限り冪等化（DELETE→INSERT、ON CONFLICT 想定）して部分失敗時のデータ保全を重視。

### 変更
- 初期リリースのため該当なし。

### 修正
- 初期リリースのため該当なし。

### 注意（運用）
- OpenAI API キーは引数で注入可能（api_key）か環境変数 `OPENAI_API_KEY` を設定する必要がある。未設定時は ValueError を送出する関数あり（news_nlp.score_news, regime_detector.score_regime）。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を起点）を探索して行うため、配布後でも CWD に依存しない。ただしルートが見つからない場合は自動ロードをスキップする。
- DuckDB バージョン互換性への配慮があり、executemany に空リストを渡さない等の安全処理を行っている。
- AI API 呼び出しは 429/ネットワーク/タイムアウト/5xx をリトライ対象とするが、その他のエラーやレスポンスパース失敗はフェイルセーフとしてスキップし続行する設計（ログ出力あり）。
- calendar_update_job や ETL ジョブは外部 API（J-Quants）呼び出しに依存するため、実行環境での認証情報とネットワークの準備が必要。

今後の予定（例）
- strategy / execution / monitoring の実装拡張（現状パッケージ構成を公開済み）。
- パフォーマンス最適化およびより詳細な品質チェックルールの追加。
- CI 用のテストケースとサンプルデータによる回帰テスト整備。

---  
（この CHANGELOG はコードベースの実装内容に基づいて作成しています。実際のリリースノートとして公開する際は、実運用での検証結果やリリース手順に応じて追記・調整してください。）