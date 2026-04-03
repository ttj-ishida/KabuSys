# CHANGELOG

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」フォーマットに準拠しています。

## [0.1.0] - 2026-04-03

初回公開リリース。本リリースでは日本株自動売買プラットフォームの基盤となる以下のコンポーネントを実装しました。各コンポーネントはテスト容易性・フェイルセーフ・ルックアヘッドバイアス回避といった設計方針を踏まえて実装されています。

### 追加 (Added)
- パッケージ基本情報
  - kabusys パッケージ初期化（src/kabusys/__init__.py）。バージョンは 0.1.0、公開モジュールは data / research / ai / … を想定。

- 設定管理 (.env 読み込み)
  - 環境変数・設定管理モジュールを実装（src/kabusys/config.py）。
    - .env / .env.local の自動読み込み機能（プロジェクトルートを .git / pyproject.toml から探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化。
    - export KEY=val 形式やシングル/ダブルクォート、エスケープ、インラインコメント対応のパーサ実装。
    - OS 環境変数を保護する protected 上書き制御（.env.local は override）。
    - Settings クラス（settings インスタンス）を提供。主要プロパティ:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須取得関数 _require）
      - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
      - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
      - DUCKDB_PATH, SQLITE_PATH（デフォルトパス）
      - 監視用 PID/KILL ファイルパス、閾値（CPU/MEM/DISK）
      - KABUSYS_ENV（development / paper_trading / live 検証）と LOG_LEVEL 検証、is_live/is_paper/is_dev 判定器

- データ: カレンダー管理
  - JPX マーケットカレンダー管理（src/kabusys/data/calendar_management.py）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - market_calendar テーブルがない場合は曜日ベースでフォールバック（週末非営業日）。
    - DB 登録値優先、未登録日は曜日フォールバックで一貫した挙動。
    - calendar_update_job にて J-Quants からの差分取得・バックフィル・保存処理を実装（健全性チェックあり）。
    - 最大探索範囲制限 (_MAX_SEARCH_DAYS) による無限ループ防止。

- データ: ETL / パイプライン
  - ETLResult データクラスを公開（src/kabusys/data/pipeline.py / etl.py）。
    - ETL 実行結果（取得件数・保存件数・品質問題・エラー）を表現。
    - has_errors / has_quality_errors / to_dict を提供。
  - ETL モジュール（pipeline.py）に差分更新・バックフィル・品質チェックを行う方針の土台を実装（J-Quants クライアント経由の取得・保存想定）。
    - デフォルトのバックフィル日数やカレンダー先読みなどの定数を設定。
    - DuckDB テーブル存在チェック・最大日付取得ユーティリティを実装。

- AI（自然言語処理）モジュール
  - ニュース NLP（銘柄ごとのセンチメントスコアリング）実装（src/kabusys/ai/news_nlp.py）。
    - raw_news / news_symbols を元に、JST の前日 15:00 ～ 当日 08:30 のウィンドウを対象にニュースを集約。
    - 1 銘柄あたり記事数上限・文字数上限でトリミング。複数銘柄を最大 20 銘柄単位でバッチ送信。
    - OpenAI（gpt-4o-mini）を Chat Completions JSON mode で呼び出し、{"results": [{"code":"XXXX","score":0.0}, ...]} を期待。
    - 429 / ネットワークエラー / タイムアウト / 5xx は指数バックオフでリトライ（最大リトライ回数の設定あり）。
    - レスポンスの厳密バリデーション（JSON 復元ロジック、results 配列検査、コード照合、数値チェック）。
    - スコアは ±1.0 にクリップ。部分成功時は該当コードのみ DELETE→INSERT で置換し、既存データ保護。
    - API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュース LLM センチメント（重み 30%）を合成して日次レジームを判定（bull/neutral/bear）。
    - prices_daily から ma200_ratio を算出（target_date 未満のデータのみ使用しルックアヘッド回避）。
    - raw_news をマクロキーワードでフィルタしてタイトルを抽出、OpenAI により macro_sentiment を評価（記事なし時は LLM 呼び出しをスキップ、0.0 フェイルセーフ）。
    - レジームスコアは clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1,1) で算出し閾値によりラベル化。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT。失敗時は ROLLBACK と例外伝播）。
    - API 呼び出しは独立実装でモジュール結合を抑制。OpenAI の一時エラーや 5xx に対するリトライ／フォールバックロジックを実装。

- Research（因子・特徴量探索）
  - factor_research モジュール（src/kabusys/research/factor_research.py）
    - モメンタム: mom_1m, mom_3m, mom_6m、ma200_dev（200 日 MA 乖離）を計算。
    - ボラティリティ/流動性: atr_20（20日 ATR）、atr_pct、avg_turnover（20日平均売買代金）、volume_ratio を計算。
    - バリュー: per（price/EPS）、roe（raw_financials の最新値）を計算。
    - DuckDB 上の SQL/ウィンドウ関数を用いた実装で、データ不足時は None を返す設計。
  - feature_exploration モジュール（src/kabusys/research/feature_exploration.py）
    - 将来リターン calc_forward_returns（任意ホライズン、horizons のバリデーションあり）。
    - Information Coefficient（Spearman の ρ）を計算する calc_ic（ランク化・欠損フィルタリングを行う）。
    - ランキングユーティリティ rank（同順位は平均ランク）。
    - factor_summary（count/mean/std/min/max/median）統計サマリーを実装。
  - research パッケージの __all__ で主要関数を公開。

- データアクセス補助
  - data.etl に ETLResult の再エクスポート（使いやすさのため）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### 既知の設計上の注意 / 実装ノート
- ルックアヘッドバイアス対策:
  - AI モジュール・研究モジュールともに内部で datetime.today() や date.today() を参照しない（必ず target_date を引数に取り、データ抽出は target_date 未満 / 対応ウィンドウで限定）。
- フェイルセーフ設計:
  - OpenAI API 呼び出し失敗やパース失敗時は例外を上位へ投げず、0.0 または空スコアにフォールバックして継続する部分がある（ただし、DB 書き込み失敗等の致命的エラーは伝播）。
- DuckDB 互換性:
  - executemany に空リストを渡すとエラーとなる DuckDB（0.10 系）を考慮して、空チェックを明示的に行ってから executemany を呼び出す実装がある。
- OpenAI 連携:
  - gpt-4o-mini を想定し JSON mode（response_format={"type":"json_object"}）での呼び出しを使用。
  - API キーは api_key 引数優先、なければ環境変数 OPENAI_API_KEY を参照。
- .env パーサ:
  - エスケープやクォート内の処理、インラインコメント判定などの細かい仕様に対応しています。
- DB 書き込み:
  - AI スコアやレジーム等は冪等に書き込む（DELETE→INSERT）ことで、再実行可能な設計。

### セキュリティ (Security)
- （初回リリースのため該当なし）

---

今後の予定（短期ロードマップ・例）
- ETL の実行エントリポイントとジョブスケジューラ統合の提供
- モニタリング / 実行モジュール（execution / monitoring）実装の追加
- テストカバレッジ拡充（特に OpenAI 呼び出しのモック化・回帰テスト）
- パフォーマンス最適化（大規模記事/銘柄のバッチ処理改善、並列化検討）

ご要望があれば、リリースノートを英語版に翻訳したり、セクションをより詳細に分割して出力します。