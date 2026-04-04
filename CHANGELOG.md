# Changelog

すべての重要な変更点をこのファイルに記録します。  
この変更履歴は「Keep a Changelog」の形式に準拠しています。  

- リリース日付はソースコードのスナップショットから推測して記載しています。
- 各項目はコード内容から推測してまとめたもので、実際のコミット履歴とは異なる場合があります。

## [Unreleased]

（現時点のスナップショットはバージョン 0.1.0 リリース相当の機能を含みます。今後の変更はここに記載します。）

---

## [0.1.0] - 2026-04-04

初回公開リリース。以下の主要機能と実装方針を提供します。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開（src/kabusys/__init__.py）。サブパッケージとして data, strategy, execution, monitoring を公開。
  - バージョン情報: __version__ = "0.1.0"。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートの自動検出: .git または pyproject.toml を起点に探索（CWD 非依存）。
    - 読み込み優先順: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサを実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応）。
  - protected keys を用いた上書き制御（OS 環境変数保護）。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB /監視 / システム設定（KABUSYS_ENV, LOG_LEVEL 等）を型付きプロパティで取得・バリデーション。
    - KABUSYS_ENV と LOG_LEVEL の許容値チェックを実装。
    - パスは Path 型で返却（expanduser 対応）。
    - 監視用フラグ（pid, kill flag, CPU/MEM/DISK 閾値など）を提供。

- AI ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news / news_symbols から銘柄ごとに記事を集約して OpenAI（gpt-4o-mini）へ送信し、銘柄別センチメント ai_score を ai_scores テーブルへ保存するワークフローを実装。
  - ニュース収集ウィンドウ計算（JST 基準の前日 15:00 ～ 当日 08:30 → UTC 変換）を提供（calc_news_window）。
  - バッチ処理:
    - 1 API コールあたり最大 20 銘柄（_BATCH_SIZE）。
    - 1 銘柄あたり最大記事数と文字長をトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
  - API 呼び出しに対してリトライと指数バックオフを実装（429/ネットワーク断/タイムアウト/5xx を対象）。
  - JSON Mode のレスポンスを厳密に検証・復元（前後余分なテキストの復元ロジックを含む）して結果をパース。
  - スコアは ±1.0 にクリップ。部分失敗時も既存スコアを保護するため、書き込みは対象コードのみ削除→挿入の冪等処理を行う。
  - テスト容易性のため OpenAI 呼び出し部分は差し替え可能（_call_openai_api を patch 可能）。

- AI 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321（日経225 連動 ETF）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して market_regime に日次判定を保存する機能を実装。
  - prices_daily から ma200_ratio を計算するロジック（ルックアヘッド防止のため target_date 未満データのみ使用）。
  - マクロキーワードによる raw_news フィルタ機能と LLM での macro_sentiment スコア化（gpt-4o-mini、JSON 出力想定）。
  - LLM 呼び出し失敗時は macro_sentiment=0.0 として継続するフェイルセーフ。
  - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で行い、失敗時は ROLLBACK を行う。

- データプラットフォーム — カレンダー管理（src/kabusys/data/calendar_management.py）
  - JPX マーケットカレンダー管理ロジックを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が未取得の場合は曜日ベース（平日を営業日）でフォールバック。
    - 最大探索範囲制限 (_MAX_SEARCH_DAYS)、先読み (_CALENDAR_LOOKAHEAD_DAYS)、バックフィル (_BACKFILL_DAYS)、健全性チェックを実装。
  - calendar_update_job を実装し、J-Quants クライアント（jquants_client）を使って差分取得→保存（冪等保存）を行う夜間バッチ処理を提供。

- データ ETL パイプライン（src/kabusys/data/pipeline.py / etl.py）
  - ETLResult データクラスを公開（etl.py で ETLResult を再エクスポート）。
  - 差分更新・バックフィル・品質チェックを想定した ETL の骨子を実装（jquants_client との連携想定）。
  - ETLResult に品質問題・エラー集約機能（to_dict）を実装。

- 研究（research）モジュール（src/kabusys/research/*）
  - ファクター計算（factor_research.py）
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（データ不足時の None ハンドリング）
    - calc_volatility: 20日 ATR, atr_pct, avg_turnover, volume_ratio（欠損対応）
    - calc_value: PER（EPS が 0/欠損時は None）, ROE（raw_financials からの最新値）
  - 特徴量探索（feature_exploration.py）
    - calc_forward_returns: 各ホライズン（デフォルト [1,5,21]）の将来リターン計算（入力検証あり）
    - calc_ic: Spearman（ランク）による Information Coefficient を実装（レコード不足時は None）
    - rank: 同順位を平均ランクで扱うランク付け（丸めによる ties 対策あり）
    - factor_summary: count/mean/std/min/max/median の統計サマリーを算出
  - zscore_normalize を data.stats から再公開（research パッケージの __init__ でまとめて公開）。

### 変更 (Changed)
- 実装設計方針（共通）
  - すべての時間窓計算・DB クエリは datetime.today()/date.today() に依存しない設計を優先（ルックアヘッドバイアス防止）。
  - OpenAI 呼び出し関連はテスト差し替えポイントを用意し、モジュール間のプライベート関数共有を避ける設計。

### 修正 (Fixed)
- 冪等性・安全性向上
  - DB への書き込みは冪等性を考慮（DELETE → INSERT、ON CONFLICT 想定）し、部分失敗時に他データを保持する実装。
  - OpenAI API のエラー処理で 5xx とそれ以外を区別してリトライ制御を行う（APIError の status_code を安全に取得）。

### 既知の制限 / TODO（コード内コメントより）
- calc_value: PBR・配当利回りは未実装（将来的な拡張ポイント）。
- news_nlp / regime_detector の OpenAI モデルは gpt-4o-mini に設定されているが、利用環境の API 方針に応じた設定変更や追加のレート制御が必要になる可能性あり。
- DuckDB の executemany に空リストを渡せない制約に対するワークアラウンドを実装（空チェック）しているが、DuckDB バージョンによっては挙動差があり得る。

### セキュリティ (Security)
- OpenAI API キーを環境変数（OPENAI_API_KEY）か関数引数で渡す方式を採用。明示的なキーのハンドリング/ログ出力回避に配慮している（キー内容をログに出さない設計）。

---

過去のリリース履歴は本リポジトリの最初のスナップショットに基づくため、将来のコミットに合わせてこの CHANGELOG を更新してください。