# Changelog

すべての注記は Keep a Changelog の形式に従います。  
このリポジトリはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-29

### 追加 (Added)
- パッケージの初期公開
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - パッケージルートでのエクスポート: data, strategy, execution, monitoring

- 環境設定/ローディング機能
  - settings を提供する `kabusys.config` モジュールを追加。
  - .env ファイルまたは環境変数から設定を読み込む仕組みを実装。
  - 自動ロードの挙動:
    - プロジェクトルート（.git または pyproject.toml）を基準に .env を探索して自動読み込み。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - OS 環境変数は保護（protected）され、.env の上書きを制御。
  - .env パーサーの強化:
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - クォート無し時のインラインコメント扱い（直前がスペース/タブの場合にコメントと判定）。
  - Settings クラスで必要な設定値をプロパティとして公開（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - DB パス設定（duckdb, sqlite）、環境判定（development / paper_trading / live）、ログレベル検証を実装。

- AI（NLP）モジュール
  - `kabusys.ai.news_nlp`:
    - raw_news と news_symbols を元に銘柄別にニュースを集約し、OpenAI（gpt-4o-mini）でセンチメント分析して ai_scores テーブルへ書き込む処理を実装。
    - 時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する `calc_news_window` を提供。
    - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄当たり記事数上限（10 件）、文字数トリム（3000 文字）などのトークン肥大化対策を実装。
    - API 呼び出しのエクスポネンシャルバックオフ（429・ネットワーク断・タイムアウト・5xx を対象）を実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、キー/型チェック、未知コードの無視、数値の有限性チェック）、スコアの ±1.0 クリップを実装。
    - DuckDB の executemany に対する互換性考慮（空リストを避ける処理）を実装。
    - テストしやすさのため内部の API 呼び出し関数を patch 可能に設計（_call_openai_api の差し替え）。

  - `kabusys.ai.regime_detector`:
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）と、ニュースベースの LLM マクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定する処理を実装。
    - ma200_ratio の計算（target_date 未満のデータのみ使用してルックアヘッドを防止）。
    - マクロキーワードフィルタで raw_news のタイトルを抽出し、OpenAI（gpt-4o-mini）でマクロセンチメントを評価。記事が無ければ LLM 呼び出しを行わず macro_sentiment=0.0 とする。
    - API 呼び出しのリトライ・エラーハンドリング（RateLimitError, APIConnectionError, APITimeoutError, APIError の 5xx 判定含む）。最終的に API 失敗時はフェイルセーフで macro_sentiment=0.0 を採用。
    - レジームスコア合成（重み付け、クリップ）と market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - テスト用に _call_openai_api をパッチ可能に設計。

- リサーチ / ファクター計算
  - `kabusys.research.factor_research`:
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Value（PER, ROE）、Volatility（20日 ATR）および流動性指標（20日平均売買代金、出来高比率）を DuckDB 上で計算する関数を実装:
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)
    - データ不足時の None 処理やログ出力を実装。SQL ウィンドウ関数を活用。
    - DuckDB のみ参照し、外部 API や実際の発注系とは独立。

  - `kabusys.research.feature_exploration`:
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク化ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - IC はスピアマンのランク相関を自前実装（ties は平均順位）。有効レコードが 3 未満なら None を返す。
    - 外部ライブラリに依存しない純粋 Python 実装。

  - `kabusys.research.__init__` で主要関数を再エクスポート（zscore_normalize を含む）。

- データプラットフォーム（Data）モジュール
  - カレンダー管理（kabusys.data.calendar_management）:
    - JPX マーケットカレンダーの夜間バッチ更新 job（calendar_update_job）を実装（J-Quants API から差分取得し market_calendar へ冪等保存）。
    - 営業日判定・前後営業日取得・期間内営業日取得・SQ 判定等のユーティリティを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータがない場合は曜日ベース（土日非営業日）でフォールバックする一貫した仕様。
    - 最大探索幅やバックフィル、健全性チェックなど安全ガードを実装。

  - ETL パイプライン（kabusys.data.pipeline）:
    - ETL の差分更新・保存・品質チェックを行う基盤を実装。
    - ETL 実行結果を表すデータクラス ETLResult を定義（target_date, fetched/saved counts, quality_issues, errors 等）。
    - 内部ユーティリティとしてテーブル存在チェック、最大日付取得などを実装。
    - デフォルトのバックフィル、Calendar lookahead 等の設定を備える。

  - `kabusys.data.etl` は pipeline.ETLResult を再エクスポート。

### 変更 (Changed)
- 設計上の方針・実装ノートを多数追加してドキュメント化
  - ルックアヘッドバイアス回避のため、全ての日付ベースの処理で datetime.today() / date.today() を直接参照しないように設計 (関数呼び出し側で target_date を渡すスタイル)。
  - OpenAI 呼び出し周りはモジュール毎に独立実装とし、モジュール間でプライベート関数を共有しないことで結合度を下げテストしやすくした。

### 修正 (Fixed)
- API 呼び出し/レスポンスの堅牢化
  - OpenAI のレスポンス JSON が前後に余計なテキストを含む稀なケースに対して「最外の { ... } を抽出してパースする」復元処理を追加。
  - network/429/timeout/5xx エラーに対するリトライ・バックオフ処理を追加し、最終的に失敗しても処理を継続するフェイルセーフ挙動を明確化。
  - DuckDB executemany の互換性問題（空リストバインド不可）を考慮した空チェックを追加。

### 注意事項 / マイグレーション (Notes)
- OpenAI API キー:
  - news_nlp.score_news と regime_detector.score_regime は api_key 引数を受け取ります。引数を省略すると環境変数 OPENAI_API_KEY を参照します。未設定時は ValueError を送出します。
- 自動 .env 読み込み:
  - パッケージは起動時にプロジェクトルートを探索して .env を自動で読み込みます。CI／テストで自動ロードを抑止したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB バージョン互換性:
  - DuckDB 0.10 系の executemany による空リストバインドの問題に配慮した実装になっています。将来的に DuckDB の挙動が変わる場合は影響を受ける可能性があります。
- テストのしやすさ:
  - OpenAI 呼び出し箇所は内部関数（_call_openai_api）を unittest.mock.patch 等で差し替え可能にしてあります。ユニットテストでは外部 API をモックすることを推奨します。

### セキュリティ (Security)
- 現状、特記すべきセキュリティ修正はありません。

---

以上が初期リリース 0.1.0 の主な変更点・設計意図の要約です。README や各モジュールの docstring にも設計方針・使用例を記載していますので、詳細は該当モジュールを参照してください。