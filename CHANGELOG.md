# Changelog

すべての変更は Keep a Changelog の仕様に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-03-27
初回リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を公開。
  - エントリポイントで主要サブパッケージをエクスポート: data, research, ai, config など。

- 環境設定管理 (kabusys.config)
  - .env / .env.local をプロジェクトルートから自動ロード（優先順: OS 環境変数 > .env.local > .env）。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ実装:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォートとバックスラッシュエスケープを考慮した値抽出。
    - クォート無しの場合のインラインコメント判定（直前がスペース/タブの '#' をコメントとみなす）。
  - 環境変数の読み取りラッパ Settings を提供（プロパティ経由で取得）:
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（未設定時は ValueError）。
    - 任意/デフォルト値: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH。
    - システム設定: KABUSYS_ENV（development/paper_trading/live のバリデーション）、LOG_LEVEL（DEBUG..CRITICAL のバリデーション）。
    - ヘルパープロパティ: is_live, is_paper, is_dev。

- AI 関連（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini、JSON Mode）で銘柄ごとのセンチメントを評価して ai_scores テーブルに保存。
    - 対象時間ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC naive datetime を使用）。
    - 大量銘柄への対応: 最大 20 銘柄/バッチ（_BATCH_SIZE）。
    - 1 銘柄あたり最新記事最大 10 件、最大 3000 文字でトリム（トークン肥大化対策）。
    - レスポンス検証を実装（JSON 抽出、results リスト、code/score 検査、数値変換、既知コードのみ採用、±1.0 でクリップ）。
    - エラー耐性: 429 / ネットワーク断 / タイムアウト / 5xx を指数バックオフでリトライ。その他はスキップして継続（フェイルセーフ）。
    - 書き込みは冪等（DELETE → INSERT、部分失敗時に既存スコア保護）。
    - テスト容易性: OpenAI 呼び出し部を差し替え可能（内部関数 patchable）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム判定（bull/neutral/bear）。
    - ma200_ratio は target_date 未満のデータのみを使用（ルックアヘッド防止）。データ不足時は中立 (1.0) を返す。
    - マクロ記事抽出はマクロキーワードリストに基づくフィルタ。
    - OpenAI 呼び出しは JSON モード使用、リトライ・バックオフ実装。API 失敗時は macro_sentiment=0.0 にフォールバック。
    - 判定結果は market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。DB 書き込み失敗時はロールバックして例外を伝播。
    - OpenAI の API キー注入をサポート（api_key 引数または環境変数 OPENAI_API_KEY）。

- データ（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分更新フロー、バックフィル、品質チェックを考慮した ETLResult データクラスを提供。
    - ETLResult: 取得/保存数、品質問題リスト、エラーリストを保持。has_errors / has_quality_errors / to_dict を提供。
    - DuckDB を前提にした最大日付取得やテーブル存在チェックなどのユーティリティ実装。
  - ETL の公開インターフェースとして ETLResult を再エクスポート（kabusys.data.etl）。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar を元に営業日判定（is_trading_day）、SQ 判定（is_sq_day）、前後営業日取得（next_trading_day / prev_trading_day）、期間内営業日列挙（get_trading_days）を提供。
    - DB にデータがない場合は曜日ベースのフォールバック（週末を非営業日と扱う）。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存（バックフィルと健全性チェックを実装）。
    - 探索範囲の上限を設定して無限ループを防止（_MAX_SEARCH_DAYS 等）。
    - date 型を厳格に扱い timezone 混入を防止。
  - データアクセスは jquants_client（外部クライアントモジュール）経由で取得・保存する想定。

- Research（kabusys.research）
  - factor_research
    - Momentum: 約1M/3M/6M リターン（営業日ベース）、200 日 MA 乖離（ma200_dev）。
    - Volatility / Liquidity: 20 日 ATR（atr_20）、ATR 比率（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）。
    - Value: PER（EPS が 0/欠損時は None）、ROE（raw_financials から最新報告を結合）。
    - DuckDB SQL を用いる実装で prices_daily/raw_financials のみ参照。データ不足時は None を返す。
  - feature_exploration
    - 将来リターン calc_forward_returns（任意ホライズン、デフォルト [1,5,21]）、ホライズン検証（1..252）。
    - IC 計算 calc_ic（スピアマンのランク相関、有効レコード 3 未満は None）。
    - ランク変換関数 rank（同順位は平均ランク、丸めで ties の検出漏れを防止）。
    - 統計サマリー factor_summary（count/mean/std/min/max/median を算出）。

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### 削除 (Removed)
- （初版のため該当なし）

### セキュリティ (Security)
- OpenAI API キーを取り扱う箇所は引数注入および環境変数からの読み取りを明示し、未設定時は例外を投げて明示的に扱う実装とした。

---

注意事項・設計上のポイント
- ルックアヘッドバイアス回避: 多くのモジュールで datetime.today()/date.today() を内部で参照せず、呼び出し側から target_date を渡す設計。
- フェイルセーフ: AI 呼び出し失敗時や外部 API エラー時は例外を即時上げずにフォールバック（スコア=0.0 など）して処理を継続する箇所があるため、呼び出し元での結果確認を推奨。
- DuckDB 前提: データ処理は DuckDB 接続を前提としているため、運用時は DuckDB のスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials, market_regime 等）を用意する必要がある。
- テスト性: OpenAI 呼び出し部分は内部関数を patch して差し替え可能に設計。

今後の想定追加項目（例）
- 発注・実行周りの execution モジュール（現在 __all__ に含むが詳細未提示）
- 監視・モニタリング向け機能の拡張（Slack 通知等）

--- 
この CHANGELOG は、コードベースの現状（初期実装）から推測して作成しています。実際のリリースノート作成時はリリース担当者が必要に応じて加筆・修正してください。