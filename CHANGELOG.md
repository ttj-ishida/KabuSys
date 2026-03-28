# CHANGELOG

すべての重要な変更点は Keep a Changelog の形式に従って記載しています。  
初回リリースに相当するバージョン 0.1.0 の変更点を日本語でまとめています。

全般的な方針・設計上の注記
- ライブラリ内部での時刻参照については、ルックアヘッドバイアスを避けるため datetime.today()/date.today() を直接参照しない設計を多用しています（各関数は target_date を受け取る）。  
- OpenAI（gpt-4o-mini）呼び出しは JSON Mode を利用し、レスポンスの頑健なパース・バリデーション・リトライ戦略（指数バックオフ）を組み込んでいます。  
- DuckDB を主要なローカルデータストアとして想定。executemany の空リスト回避、日付型取り扱いなど DuckDB の挙動に配慮した実装になっています。  
- テスト容易性を配慮して、OpenAI API キーや API 呼び出し処理を引数注入／モック差し替え可能に実装しています。

## [0.1.0] - 2026-03-28

### Added
- 基本パッケージ
  - 新規パッケージ `kabusys` を追加。パッケージメタ情報として `__version__ = "0.1.0"`、公開モジュールリスト `__all__ = ["data", "strategy", "execution", "monitoring"]` を定義。

- 設定 / 環境変数管理
  - `kabusys.config` モジュールを追加。
    - .env/.env.local ファイルの自動ロード機能（プロジェクトルートの検出: .git または pyproject.toml を起点）。  
    - .env 解析器の実装（コメント・export プレフィックス・クォート内のエスケープ処理・インラインコメント処理対応）。  
    - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。  
    - 環境変数の必須チェック関数 `_require` と `Settings` クラスを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等を参照）。  
    - `KABUSYS_ENV` と `LOG_LEVEL` の検証（限定された許容値）。  
    - DB パス設定（`DUCKDB_PATH`, `SQLITE_PATH`）と便利プロパティ（is_live / is_paper / is_dev）。

- AI 機能（ニュース NLP / レジーム判定）
  - `kabusys.ai.news_nlp` を追加。
    - raw_news / news_symbols を集約し、銘柄ごとにニュースをまとめて OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_score）を算出し `ai_scores` に書き込む処理を実装。  
    - JST ベースのニュースウィンドウ計算（前日15:00 JST 〜 当日08:30 JST を UTC に変換）を提供（`calc_news_window`）。  
    - バッチサイズ、記事/文字数トリム、JSON レスポンスの堅牢なバリデーション、スコアの ±1.0 クリップ、429/ネットワーク/5xx に対するリトライ（指数バックオフ）を実装。  
    - 部分成功時に既存スコアを保護するため、書き込みは対象コードのみ DELETE → INSERT（冪等性・部分失敗耐性）。  
    - テスト向けに API 呼び出し箇所を差し替え可能（unittest.mock.patch を想定）。

  - `kabusys.ai.regime_detector` を追加。
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）と、マクロ経済ニュース（news_nlp により抽出した記事の LLM センチメント、重み30%）を組み合わせて日次の市場レジーム（"bull"/"neutral"/"bear"）を判定。  
    - MA 乖離は look-ahead を防ぐため target_date 未満のデータのみ利用。記事がない・API 失敗時は macro_sentiment=0.0（フェイルセーフ）。  
    - OpenAI 呼び出しは内部で独立実装し、リトライ・エラーハンドリング（RateLimit/ネットワーク/タイムアウト/5xx）を行う。  
    - 判定結果は `market_regime` テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。

- データ基盤 / ETL
  - `kabusys.data.pipeline` を追加。
    - ETL 議論に基づく差分取得・backfill ロジック、品質チェックフック、J-Quants クライアント呼び出しのラッパー。  
    - ETL 実行結果を格納する `ETLResult` データクラスを公開（取得件数、保存件数、品質問題、エラー一覧等を含む）。  
    - DuckDB のテーブル存在チェックや最大日付取得ユーティリティ等を実装。

  - `kabusys.data.etl` モジュールで `ETLResult` を再エクスポート。

  - `kabusys.data.calendar_management` を追加。
    - JPX（日本取引所）のマーケットカレンダー管理（`market_calendar` テーブルの更新・照会）と営業日ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。  
    - calendar_update_job により J-Quants API から差分を取得して冪等保存。バックフィル・健全性チェックを実装。  
    - DB にデータがない場合は曜日ベースのフォールバック（週末を非営業日扱い）を採用し、DB がまばらな場合でも一貫した判定を提供。

- リサーチ（ファクター計算 / 特徴量探索）
  - `kabusys.research` パッケージを追加。以下を公開：`calc_momentum`, `calc_volatility`, `calc_value`, `zscore_normalize`（data.stats から）、`calc_forward_returns`, `calc_ic`, `factor_summary`, `rank`。
  - `kabusys.research.factor_research`
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR）、Value（PER/ROE）などのファクターを DuckDB SQL で計算する関数を提供。  
    - データ不足時の None 処理、スキャン範囲バッファ等を考慮。戻り値は (date, code) をキーとする dict のリスト。
  - `kabusys.research.feature_exploration`
    - 将来リターン計算（任意ホライズン）、Spearman ランク相関による IC 計算、ランク化ユーティリティ、ファクター統計サマリーを実装。  
    - 外部ライブラリに依存せず標準ライブラリ + DuckDB で完結する実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI 等の API キーは必須設定（関数呼び出し時に api_key を渡すか環境変数 OPENAI_API_KEY を設定）。設定漏れは ValueError を発生させ検出可能。  
- .env 自動ロード時、既存の OS 環境変数は保護（protected set）して上書きされない仕組みを導入。

### Notes / 実装上の注意点
- OpenAI 呼び出しで使用するモデルは現時点で `gpt-4o-mini` が指定されています。JSON Mode を利用して厳密な JSON を期待しますが、前後に余計なテキストが混ざる場合の復元処理も実装しています。  
- DuckDB のバージョン依存性（executemany に空リストを渡せない等）を考慮して、空チェックを行ってから executemany を呼ぶ実装になっています。  
- カレンダー・ETL のバッチ処理は健全性チェック（未来日付の異常）やバックフィルを取り込む挙動を持ちます。  

---

今後の予定（例）
- strategy / execution / monitoring 各モジュールの実装と統合テストの追加。  
- J-Quants クライアント（fetch/save）のスタブ化/実装の充実と、さらに詳細な品質チェックルールの追加。  
- OpenAI 呼び出しに関するメトリクス収集・監視・コスト制御機能の追加。

---

この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴やプロジェクト方針に応じて適宜調整してください。