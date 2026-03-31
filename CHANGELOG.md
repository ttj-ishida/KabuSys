CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルは、コードベース（src/kabusys 以下）の現在の実装内容から推測して作成した初期の変更履歴です。

フォーマットの注記:
- 日付は本ファイル生成日（2026-03-31）を使用しています。
- 記載は実装されているモジュール・関数・設計方針に基づく推定です。

Unreleased
----------
（なし）

0.1.0 - 2026-03-31
------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージエントリポイントを定義（src/kabusys/__init__.py）。
- 環境・設定管理
  - .env ファイル／環境変数を自動で読み込む設定ローダーを実装（src/kabusys/config.py）。
    - プロジェクトルート検出（.git または pyproject.toml を探索）により作業ディレクトリに依存しない自動ロード。
    - .env / .env.local の読み込み順と保護された OS 環境変数の上書き制御。
    - export 形式やクォート、インラインコメント等に対応した堅牢なパーサー。
    - 必須環境変数チェック用の _require、環境名（development/paper_trading/live）とログレベルのバリデーション。
    - 設定プロパティ: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト有）, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, env 判定ユーティリティ（is_live 等）。
- AI（自然言語処理）機能
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - 指定日のニュースウィンドウ計算（前日15:00 JST〜当日08:30 JST を UTC に変換）。
    - raw_news と news_symbols から銘柄別に記事を集約し、1 銘柄あたり最大記事数・最大文字数でトリム。
    - OpenAI（gpt-4o-mini）へのバッチ送信（チャンクサイズ上限20銘柄）、JSON mode を期待。
    - レート制限・ネットワーク断・タイムアウト・5xx に対するエクスポネンシャルバックオフとリトライ。
    - レスポンス検証（JSON 抽出、results 配列、code/score 検証）、スコアの ±1.0 クリップ。
    - 成功したスコアのみ ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT、トランザクション処理）。
    - テスト容易性を考慮した _call_openai_api の差し替え可能設計。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）判定。
    - prices_daily / raw_news を参照、OpenAI によるマクロセンチメント評価（gpt-4o-mini）。
    - API エラー時は安全に macro_sentiment=0.0 にフォールバック。
    - 計算結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時の ROLLBACK 処理とログ）。
    - ルックアヘッドバイアス回避（内部で datetime.today()/date.today() を参照しない、クエリに date < target_date を明示）。
- データプラットフォーム（DuckDB ベース）
  - ETL パイプラインと結果データ構造（src/kabusys/data/pipeline.py / src/kabusys/data/etl.py）
    - ETLResult データクラスを導入し、ETL 実行の取得数・保存数・品質チェック結果・エラー集約を提供。
    - 差分更新、バックフィル、品質チェック連携（jquants_client と quality モジュール想定）の設計方針を実装。
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを参照して営業日判定ロジック（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）を提供。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した動作。
    - calendar_update_job による J-Quants からの差分取得と冪等保存、バックフィルと健全性チェックの実装。
  - jquants_client を利用する想定での差分取得・保存処理に対応（モジュール境界でのエラー処理・ログ出力実装）。
- リサーチ・ファクター群（src/kabusys/research/*）
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時の None 処理。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。データ不足時の None 処理。
    - calc_value: raw_financials から最新財務（report_date <= target_date）を取得し PER/ROE を計算。EPS が 0/欠損の場合は None。
  - feature_exploration.py
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）に対応した将来リターン計算。horizons のバリデーション（正の整数、<=252）。
    - calc_ic: スピアマンランク相関（Information Coefficient）計算。必要レコード数チェック（>=3）。
    - rank: 同順位は平均ランクとする安定したランク関数（丸めで ties の検出漏れを防止）。
    - factor_summary: count/mean/std/min/max/median の統計サマリー生成。
  - research パッケージの公開 API を整備（zscore_normalize の再エクスポート等）。
- 一般的な品質・設計方針
  - ルックアヘッドバイアス防止: 多くの処理で datetime.today()/date.today() を参照しない設計。
  - DuckDB を主要 DB として使用（トランザクション、executemany の空リスト制約対策の実装）。
  - ロギング・警告出力を充実。例外発生時のロールバックやフォールバック動作を明示。
  - テスト容易性を考慮した設計（外部 API 呼び出しポイントの差し替え可能性）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / 実装上の注意点（ドキュメント）
- OpenAI API キーは関数引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出して明示。
- ai モジュールは外部 API（OpenAI）依存があるため、テスト時は _call_openai_api をモックすることを推奨。
- DuckDB バインドや executemany の挙動により、空リストを渡すとエラーとなる箇所を考慮している（空チェックを経てから executemany を実行）。
- calendar_update_job と ETL 処理は外部 J-Quants クライアント（jquants_client）に依存。API の例外は捕捉してログ化し、ゼロ件返却で呼び出し側に処理継続の判断を委ねる設計。

今後の想定（未実装・改善予定の例）
- より詳細なモニタリング・メトリクス出力（Prometheus など）。
- ai スコアの履歴管理やバージョン情報の埋め込み。
- ETL の並列化・差分最適化、品質チェックの自動復旧アクション。
- 追加のリサーチ指標（PBR、配当利回り等）やバックテスト用ユーティリティの拡充。

--- 

この CHANGELOG は現行のソースコード（src/kabusys 以下）の構成・実装から推測して作成しています。不明点や追記したい情報（リリース日・コミットハッシュ・既知の問題など）があれば教えてください。必要に応じてバージョンや項目を編集します。