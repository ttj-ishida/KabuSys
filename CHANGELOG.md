# CHANGELOG

すべての重要な変更をここに記録します。フォーマットは "Keep a Changelog" に準拠します。

## [0.1.0] - 2026-04-03

初期リリース。日本株自動売買システム「KabuSys」のコア機能群を実装・公開します。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ全体
  - パッケージ名: kabusys、バージョン 0.1.0 を設定。
  - パブリックモジュール: data, strategy, execution, monitoring をエクスポート。

- 環境設定 (src/kabusys/config.py)
  - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロード無効化可能。
  - .env パーサの実装:
    - export キーワード対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、
    - インラインコメント処理（クォート有無での挙動差）を考慮した堅牢なパース。
  - Settings クラスを提供（settings インスタンスをエクスポート）。
    - J-Quants / kabuステーション / LINE / DB / 監視 / システム関連の設定プロパティ（例: jquants_refresh_token, kabu_api_password, duckdb_path, pid_file_path 等）。
    - KABUSYS_ENV（development, paper_trading, live の検証）および LOG_LEVEL（DEBUG/INFO/...）の検証ロジック。
    - パスや閾値（CPU/MEM/DISK）を Path/float に変換するユーティリティ。

- AI（自然言語処理）モジュール (src/kabusys/ai)
  - ニュースセンチメントスコアリング (news_nlp.py)
    - score_news(conn, target_date, api_key=None): raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini, JSON mode）で銘柄ごとのセンチメント（-1..1）を取得して ai_scores テーブルへ保存。
    - タイムウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
    - バッチ処理（最大 20 銘柄/コール）、1銘柄あたり記事数上限・文字数トリミング、エクスポネンシャルバックオフによるリトライ、レスポンスバリデーション、スコアのクリップ、部分成功時の idempotent な DB 書き換え（DELETE → INSERT）。
    - テスト容易性のため _call_openai_api をモック差し替え可能に設計。
  - 市場レジーム判定 (regime_detector.py)
    - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルへ冪等保存。
    - ma200_ratio 計算（target_date 未満のデータのみ使用でルックアヘッド防止）。データ不足時は中立 (1.0) をフォールバック。
    - マクロキーワードで raw_news をフィルタして LLM に渡す。LLM 呼び出しは専用の _call_openai_api を使用し、リトライ/フェイルセーフを実装。
    - レジームラベル（bull/neutral/bear）判定基準とログ出力。
    - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等パターン、例外時に ROLLBACK を行う。

- データプラットフォーム (src/kabusys/data)
  - マーケットカレンダー管理 (calendar_management.py)
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days といった営業日判定ユーティリティを提供。
    - market_calendar テーブルが未登録の時は曜日ベース（土日非営業）でのフォールバックを採用し、一貫した挙動（DB 優先、未登録はフォールバック）を保証。
    - calendar_update_job(conn, lookahead_days) により J-Quants から差分取得 → market_calendar へ冪等的保存を行う（バックフィル・健全性チェック含む）。
    - 最大探索日数制限や sanity check により無限ループや極端な未来値の取り込みを防止。
  - ETL パイプライン (pipeline.py / etl.py)
    - ETLResult データクラスを実装（取得件数・保存件数・品質問題・エラー一覧等を格納、to_dict を提供）。
    - 差分更新・バックフィル・品質チェックの方針を文書化。
    - 内部ユーティリティ: テーブル存在チェックや最大日付取得などの基盤関数を実装。
    - etl モジュールは ETLResult を再エクスポート。

- 研究・ファクター計算 (src/kabusys/research)
  - factor_research.py
    - calc_momentum(conn, target_date): mom_1m/mom_3m/mom_6m、ma200_dev 等を prices_daily から計算（データ不足時は None）。
    - calc_volatility(conn, target_date): 20日 ATR / 相対 ATR、20日平均売買代金、出来高比率等を計算。
    - calc_value(conn, target_date): raw_financials から最新財務を取得して PER/ROE を計算（EPS 0/NULL は None）。
    - DuckDB のウィンドウ関数を併用し、営業日ベースの窓を考慮した実装。
  - feature_exploration.py
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン（翌日・翌週・翌月等）を一括 SQL で取得する効率的実装。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマン（ランク）相関を算出し、データ不足時は None を返す。
    - rank(values): 同順位は平均ランクとするランク変換（float の丸めで ties を安定検出）。
    - factor_summary(records, columns): count/mean/std/min/max/median を返す統計サマリーを提供。
  - research パッケージは主要関数を __all__ で集約して再エクスポート。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 注意点 / 設計上の決定 (Notes)
- ルックアヘッドバイアス防止:
  - AI モジュールやリサーチ関数は内部で datetime.today()/date.today() を参照せず、必ず引数の target_date を基準に処理します。
- フェイルセーフ設計:
  - OpenAI API 呼び出し失敗時は例外を投げずフォールバック（0.0 スコアやスキップ）して処理継続する箇所があるため、外部 API の不安定性に耐性があります（一部致命的な DB 書き込み失敗等は例外が上位に伝播）。
- テストへの配慮:
  - OpenAI 呼び出し部分（_call_openai_api）はモック差し替えを想定した設計。
- DuckDB 互換性:
  - executemany の空リスト回避や LIST 型パラメータの回避など、DuckDB のバージョン差異を考慮した実装を行っています。
- セキュリティ・運用:
  - 環境変数の自動ロードは OS 環境変数を保護する仕組み（protected set）を採用。

### 既知の制限 (Known limitations)
- strategy / execution / monitoring パッケージの詳細実装は本リリースでは参照される構成になっているが、ここに含まれるコードは主にデータ・研究・AI 周りに集中しています。
- OpenAI API の JSON mode を前提にパース処理を行うため、将来の API 仕様変更に対して追加対応が必要になる可能性があります。

---

今後のリリースでは、strategy レイヤ（売買シグナル生成・ポートフォリオ構築）、execution（発注ロジック・kabu API 連携）、monitoring（プロセス監視・アラート）など運用側機能の充実、品質チェックの自動通知、テストカバレッジ強化を予定しています。