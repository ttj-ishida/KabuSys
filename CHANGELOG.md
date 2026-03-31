# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
リリース日はソースコードの現状に基づく推定日付です。

<!--
参考: https://keepachangelog.com/ja/1.0.0/
-->

## [Unreleased]

（現時点のコードベースは初回公開版に相当するため、主要な変更点は 0.1.0 に記載しています。
今後の変更はここに追記してください。）

## [0.1.0] - 2026-03-31

初回リリース。日本株自動売買システム「KabuSys」の基盤モジュール群を実装。

### 追加 (Added)

- パッケージ基礎
  - kabusys パッケージを追加。バージョン 0.1.0 を設定。
  - 公開モジュール: data, strategy, execution, monitoring（__all__ に定義）。

- 環境設定 / 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート判定: .git または pyproject.toml を基準に探索（CWD 非依存）。
  - .env / .env.local の読み込み優先順位を実装（OS 環境変数を保護する protected 機構）。
  - .env のパース機能:
    - コメント、export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメント処理に対応。
    - 無効行のスキップや読み込み失敗時の警告出力。
  - 自動ロード無効化オプション: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - Settings クラスでアプリケーション設定を型付きプロパティとして提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, DUCKDB_PATH, KABUSYS_ENV, LOG_LEVEL など）。
  - env/log level の値検証（許容値チェック、エラー時 ValueError）。

- AI 関連 (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を集約して銘柄ごとのニュース文書を作成。
    - OpenAI (gpt-4o-mini) を用いたバッチ評価。1 API コールで最大 20 銘柄を処理。
    - 1 銘柄あたりの最大記事数 / 文字数制限（_MAX_ARTICLES_PER_STOCK=10, _MAX_CHARS_PER_STOCK=3000）によるトークン肥大化対策。
    - JSON Mode を期待し、厳密な JSON をパース。パース補助（前後テキストが混入した場合に最外側の {} を抽出）を実装。
    - エラーハンドリング: 429、ネットワーク断、タイムアウト、5xx に対する指数バックオフリトライ。その他はスキップして継続（フェイルセーフ）。
    - スコアの検証・クリッピング（±1.0）。部分失敗時に既存データを保護するため、書き込みは該当コードのみ DELETE → INSERT。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。
    - calc_news_window(target_date) により JST 時間ウィンドウを UTC naive datetime で返す（ルックアヘッド防止設計）。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して、日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースはニュース NLP のウィンドウ集約(calc_news_window)を利用し、OpenAI（gpt-4o-mini）でセンチメントを JSON 出力として取得。
    - API の冗長性対策: リトライ、サーバーエラー区別、最終的に失敗した場合は macro_sentiment=0.0 として継続するフェイルセーフ。
    - レジームスコアの合成、閾値判定、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返却。

- データプラットフォーム (kabusys.data)
  - ETL パイプライン (kabusys.data.pipeline)
    - ETLResult dataclass を追加（取得数・保存数・品質問題・エラー一覧を保持）。
    - 差分更新、バックフィル、品質チェックのためのユーティリティ関数（テーブル存在チェック、最大日付取得など）を実装。
    - 市場カレンダー補助や J-Quants クライアント統合を想定した設計（jq インタフェースを利用）。
  - ETL の公開インターフェース再公開 (kabusys.data.etl: ETLResult の再エクスポート)。
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダーの夜間バッチ更新用 calendar_update_job を実装（J-Quants から差分取得、バックフィル、健全性チェック）。
    - 営業日判定/前後営業日取得/期間内営業日リスト/is_sq_day 等のユーティリティ（DB 登録値優先、未登録日は曜日ベースでフォールバック）。
    - 最大探索日数やバックフィル日数、健全性制約を導入して無限ループや異常データを防止。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research: Momentum / Volatility / Value ファクターの計算を実装。
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率。
    - calc_value: EPS/ROE を用いた PER / ROE の算出（raw_financials から最新報告を取得）。
    - DuckDB SQL を主に利用して効率的に計算。結果は (date, code) 単位の dict のリストで返却。
  - feature_exploration: 将来リターン計算、IC（Spearman rank）計算、統計サマリー、ランク関数を実装。
    - calc_forward_returns: 任意ホライズンの将来リターンを一度のクエリで取得。ホライズン検証あり（1〜252）。
    - calc_ic: factor と将来リターンのスピアマン ρ（ties に対する平均ランク対応）。
    - factor_summary: count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクで処理（浮動小数丸め対策あり）。
  - 研究系ユーティリティをエクスポート（zscore_normalize の再エクスポート等）。

- 外部依存・設計に関する注意点（README 相当の実装方針）
  - ルックアヘッドバイアス防止: 各スコアリング/計算関数は datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る設計。
  - データベースは DuckDB を前提（DuckDB のバインド制約への配慮あり、executemany 空リスト回避等）。
  - OpenAI SDK を利用（OpenAI.OpenAI クライアント、JSON Mode）。テスト容易性のため _call_openai_api を patch して差し替え可能に設計。
  - フェイルセーフ優先の設計: API 失敗は例外で停止させず、ログ＆スコアのデフォルト値で継続する箇所がある（ただし DB 書き込み失敗等はロールバックして上位へ再送出）。

### 変更 (Changed)

- （初版のため該当なし）

### 修正 (Fixed)

- （初版のため該当なし）

### 注意 / 既知の制約 (Known issues / Notes)

- OpenAI API キーは関数引数に注入するか環境変数 OPENAI_API_KEY を設定する必要がある。未設定時は ValueError を送出。
- news_nlp/regime_detector は LLM の出力を厳密な JSON（期待スキーマ）として扱うため、モデル応答に変動があるとスコア取得が失敗する可能性がある。パース失敗時は該当チャンクをスキップして続行する設計。
- ai_score / market_regime 等のDB テーブル名やスキーマはコード側の期待に依存する（事前にスキーマ準備が必要）。
- 一部 DuckDB バインドの挙動（list バインド等）に対して互換性処理を入れているが、使用する DuckDB バージョンによっては追加の調整が必要な場合がある。
- 現バージョンでは PBR・配当利回りなど一部バリューファクターは未実装。

### セキュリティ (Security)

- （初版のためセキュリティ修正項目はなし）

---

開発者メモ:
- 今後のリリースでは、テーブルスキーマ定義、マイグレーション指示、CI テスト用のモック（OpenAI / J-Quants のスタブ）、およびサンプル .env.example を追加すると導入がさらに容易になります。