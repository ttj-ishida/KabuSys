CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
リリース日はリポジトリ内のコード（__version__）と現行日付を基に記載しています。

[0.1.0] - 2026-03-31
-------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ公開インターフェースを定義（src/kabusys/__init__.py）
    - __version__ = "0.1.0"
    - __all__ に data, strategy, execution, monitoring を含む（将来的なサブパッケージ公開を想定）

- 環境設定管理（src/kabusys/config.py）
  - Settings クラスを導入し、環境変数経由でアプリケーション設定を取得
    - 必須トークン取得用の _require() を備える（未設定時は ValueError を送出）
    - J-Quants, kabuステーション, Slack, DBパス（DuckDB/SQLite）、監視設定（PID ファイル / CPU/MEM/DISK 閾値）、実行環境（development/paper_trading/live）、ログレベル検証等をプロパティで提供
    - env 値や LOG_LEVEL のバリデーションを実装（許容値外は例外）
    - 自動 .env ロード機構を実装（プロジェクトルート検出＝.git または pyproject.toml を基準）
      - 読み込み優先順位: OS 環境変数 > .env.local > .env
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
      - .env パースは export 文、クォートやエスケープ文字、インラインコメントなどに対応
      - .env 読み込み時に既存 OS 環境変数を保護する protected 機能を実装

- AI モジュール（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - score_news(conn, target_date, api_key=None): raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON mode を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込み
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window を実装
    - バッチ処理（1回あたり最大 20 銘柄）、1銘柄あたり記事数/文字数上限でトークン肥大化を緩和
    - API 呼び出しでの 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ
    - レスポンスの堅牢なバリデーションを実装（JSON 抽出、results リスト検証、code/score 検証、スコアの有限性チェック）
    - スコアは ±1.0 にクリップ
    - DB 書き込みは部分置換（取得済みコードのみ DELETE → INSERT）により部分失敗時の既存データ保護
    - テスト容易性: _call_openai_api の差し替え（mock）を考慮した設計
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して market_regime テーブルへ冪等書き込み
    - ma200_ratio を計算する内部関数（_calc_ma200_ratio）：target_date 未満のデータのみを使用し、データ不足時は中立（1.0）にフォールバック
    - raw_news からマクロキーワードにマッチするタイトルを抽出する _fetch_macro_news を実装（最大 20 件）
    - OpenAI（gpt-4o-mini）呼び出しは独立実装で、API エラー時は macro_sentiment=0.0 にフォールバック（例外を上げず継続）
    - レジームスコアはクリップされ、閾値に基づいて "bull"/"neutral"/"bear" ラベルを付与
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等処理、失敗時は ROLLBACK を試行して上位へ例外伝播

- データ基盤（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX 市場カレンダー（market_calendar）に基づく営業日判定ユーティリティを追加:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - market_calendar がない場合は曜日ベース（土日非営業日）でフォールバックする一貫したロジック
    - next/prev の探索は _MAX_SEARCH_DAYS に制限して無限ループ防止
    - calendar_update_job(conn, lookahead_days=90): J-Quants クライアント経由で差分取得・バックフィル（直近 _BACKFILL_DAYS を再フェッチ）・保存（jq.save_market_calendar 呼び出し）を行い、健全性チェック（将来日付の異常検出）を実装
    - DB レコードの存在チェックや NULL 扱いに対する警告ログなど堅牢性を考慮
  - ETL パイプライン（src/kabusys/data/pipeline.py / etl.py）
    - ETLResult dataclass を実装して ETL 実行結果（取得数・保存数・品質問題・エラー）を集約・シリアライズ可能に
    - pipeline モジュールは差分更新、保存（jquants_client の save_* を利用）および品質チェック（quality モジュール）を想定する設計
    - _table_exists / _get_max_date 等のユーティリティを実装（DuckDB 前提）
    - etl.py で ETLResult を再エクスポート

- 研究用ユーティリティ（src/kabusys/research）
  - factor_research.py
    - calc_momentum(conn, target_date): 1M/3M/6M リターンと ma200_dev（200日MA乖離）を算出
    - calc_volatility(conn, target_date): 20日 ATR（atr_20）・相対ATR（atr_pct）・20日平均売買代金・出来高比率を算出
    - calc_value(conn, target_date): raw_financials と prices_daily を結合して PER / ROE を算出（EPS=0 や欠損は None）
    - 全関数は DuckDB の prices_daily / raw_financials のみ参照し、ルックアヘッドバイアス防止を考慮
  - feature_exploration.py
    - calc_forward_returns(conn, target_date, horizons=None): 指定ホライズンの将来リターンを一回のクエリで取得（ホライズン検証・最大探索日数のバッファを実装）
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）を計算（有効レコードが 3 未満の場合は None）
    - rank(values): 同順位は平均ランクとするランク変換を実装（丸めにより ties 検出漏れを抑止）
    - factor_summary(records, columns): count/mean/std/min/max/median を計算
  - research パッケージ __init__ で主な関数を再エクスポート

- 設計上の重要な注意点（全体）
  - ルックアヘッドバイアス防止: 各モジュールで datetime.today()/date.today() を直接参照しない設計（target_date を明示的に渡す）
  - DB 書き込みは冪等化（DELETE→INSERT など）を基本とし、部分失敗時に既存データを保護
  - OpenAI 呼び出しは JSON Mode を利用し応答パースを厳密に行う（レスポンスの冗長テキスト復元処理あり）
  - API エラーやパース失敗は多くの箇所でフェイルセーフ（デフォルト値やスキップ）により処理継続を優先
  - 単体テストを想定した差し替えポイント（例: _call_openai_api の mock）を提供

Changed
- 初回リリースのため該当なし

Fixed
- 初回リリースのため該当なし

Security
- 初回リリースのため該当なし

Notes / Known limitations
- 一部関数は外部クライアント（jquants_client, OpenAI の SDK, kabu API など）への依存があるため、実行環境での適切な認証情報設定が必要
- 一部実装（例: data.pipeline の継続実装や jquants_client の具体的実装）はリポジトリ外（別モジュール）に依存
- monitoring / execution / strategy 等のパッケージは __all__ に含まれているものの、この変更セットでは提供されるサブモジュールの実装範囲が限定的（将来の実装で機能拡張予定）

---

以上はコードベースから推測して作成した CHANGELOG です。必要であれば各項目をより技術的に細分化したり、実装ファイルごとに変更箇所のコード行や例を追記できます。どの形式で追記しますか（例: モジュール別の詳細、リスク・テスト指示、リリース手順など）？