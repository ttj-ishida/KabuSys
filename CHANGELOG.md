# CHANGELOG

すべての重要な変更履歴をここに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-04-03
初回リリース

### 追加 (Added)
- パッケージの基本構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダを実装
    - プロジェクトルートの探索は __file__ を起点に .git または pyproject.toml を探索（CWD 非依存）
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env のパース機能を強化
    - export プレフィックス対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - クォートなしでのインラインコメント許容（前の文字がスペース/タブの場合）
  - protected（OS 環境変数）を保持する override ロジック
  - Settings クラスを提供（settings = Settings() で利用）
    - J-Quants / kabu ステーション / LINE / DB / 監視 / システム関連の各設定プロパティを定義
    - 必須値取得時は未設定で ValueError を送出（_require）
    - env 値検証: KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL（DEBUG/INFO/...）

- データ関連モジュール (kabusys.data)
  - カレンダー管理 (calendar_management)
    - JPX カレンダー管理用ロジックを実装
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供
    - DB にデータがない場合は曜日ベースでフォールバック（週末を非営業日扱い）
    - 夜間バッチ更新 job: calendar_update_job（J-Quants から差分取得し保存、バックフィル・健全性チェック実装）
  - ETL パイプライン基盤 (pipeline)
    - ETLResult データクラスを実装（取得件数、保存件数、品質問題、エラー等を保持）
    - ETL の差分更新・バックフィル・品質チェック方針を実装想定
  - etl.py で ETLResult を公開

- AI（自然言語処理）モジュール (kabusys.ai)
  - ニュース NLP（news_nlp）
    - raw_news / news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）へ送信
    - JSON Mode のレスポンスを検証・解析し ai_scores テーブルへ書込み
    - バッチサイズ、トークン肥大化対策（記事数・文字数のトリム）、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライを実装
    - レスポンスパースのフォールバック（前後の余計なテキストから外側の {} を抽出して復元）
    - テスト用に _call_openai_api を差し替え可能（unittest.mock.patch）
    - calc_news_window(target_date) を提供（JST 基準の前日 15:00 〜 当日 08:30 相当の UTC 範囲を返す）
    - score_news(conn, target_date, api_key=None) を提供: 書き込んだ銘柄数を返す。API キー未設定時は ValueError。
    - DuckDB executemany の挙動差異に対する互換性配慮（空リストを渡さない）
  - レジーム判定（regime_detector）
    - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロニュースセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定
    - prices_daily / raw_news を参照し、計算結果を market_regime テーブルへ冪等書き込み
    - OpenAI 呼び出し（gpt-4o-mini）・JSON Mode を使い、失敗時は macro_sentiment=0.0 でフェイルセーフ継続
    - API エラーや JSON パース失敗に対するログ・リトライ実装
    - score_regime(conn, target_date, api_key=None) を提供: 成功時 1 を返す。API キー未設定時は ValueError。

- リサーチ（研究）モジュール (kabusys.research)
  - factor_research
    - calc_momentum(conn, target_date): mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）を計算
    - calc_volatility(conn, target_date): atr_20, atr_pct, avg_turnover, volume_ratio を計算
    - calc_value(conn, target_date): per, roe を raw_financials と株価から計算
    - DuckDB を使った SQL ベースの計算（外部 API へはアクセスしない）
    - 不足データ時には None を返す設計
  - feature_exploration
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン（デフォルト: 1/5/21 日）を計算
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマン順位相関（IC）を計算
    - rank(values): 同順位は平均ランクとするランク化ユーティリティ
    - factor_summary(records, columns): count/mean/std/min/max/median を計算
  - 研究用ユーティリティを再エクスポート（__all__ に主要関数を追加）

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### 注意事項 / 実装上のポイント
- LLM（OpenAI）利用
  - 使用モデル: gpt-4o-mini（ニュース NLP / レジーム判定ともに）
  - API キーは引数 (api_key) か環境変数 OPENAI_API_KEY を使用。未設定なら ValueError を送出する仕様。
  - レスポンスは JSON モードを期待するが、パース失敗に備えた復元ロジックを実装（余分な前後文字列の切り出しなど）。
  - API 障害時は例外をそのまま上げずにフォールバックする設計（スコア 0.0 や処理スキップなど）でフェイルセーフを重視。

- ルックアヘッドバイアス対策
  - 各処理は内部で datetime.today() / date.today() を直接参照せず、target_date 引数に依存する設計。
  - DB クエリでは date < target_date のような排他条件を利用してルックアヘッドを防止。

- DuckDB 互換性への配慮
  - executemany に空リストを渡せないバージョン（例: DuckDB 0.10）を考慮して空チェックを明示的に実装。
  - 日付型の扱いは date オブジェクトを使う（timezone の混入を防止）。

- DB 書き込み
  - market_regime / ai_scores 等への書き込みは冪等（DELETE → INSERT または ON CONFLICT 相当）を意識した実装。
  - トランザクション制御（BEGIN / COMMIT / ROLLBACK）を明示的に行い、失敗時には ROLLBACK を試みる。

- 設定・検証
  - Settings.env / log_level では許容値を検証し、不正な場合は ValueError を発生させる。
  - 複数のパス（duckdb_path / sqlite_path / pid_file_path / kill_flag_path）を設定可能。

### 既知の制約・今後の改善候補
- ai モジュールは現状で OpenAI（gpt-4o-mini）に依存しているため、将来的に別ベンダーやオフラインモデル対応が必要な場合はインタフェース抽象化を検討。
- score_news のレスポンス検証は現状で厳格だが、LLM の出力多様性に対する更なる堅牢化（スキーマ検証ライブラリ等の導入）が検討対象。
- calendar_update_job / ETL の具体的な jquants_client 実装は別モジュールに分離されている（テスト用に差し替え可能）。

### 必要な環境変数（主なもの）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で必須）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン
- KABU_API_PASSWORD: kabu ステーション API のパスワード
- KABUSYS_ENV: 実行環境（development | paper_trading | live）
- その他: DUCKDB_PATH, SQLITE_PATH, LINE_CHANNEL_ACCESS_TOKEN 等（Settings に一覧）

---

今後のリリースでは、発注実行部分（execution）、戦略定義（strategy）、監視（monitoring）などの実装拡充、テストカバレッジやドキュメントの追加を予定しています。