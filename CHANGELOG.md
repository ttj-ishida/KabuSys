CHANGELOG
=========

この CHANGELOG は Keep a Changelog の形式に準拠しています。  
（コードベースから推測できる機能追加・設計方針・注意点を記載しています）

Unreleased
----------

（なし）

0.1.0 - 2026-04-03
------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ公開情報（src/kabusys/__init__.py）にて version="0.1.0" を設定。

- 環境設定 / 設定読み込み（src/kabusys/config.py）
  - .env / .env.local ファイルまたは OS 環境変数から設定を自動読み込みする仕組みを実装（プロジェクトルート判定: .git または pyproject.toml を探索）。
  - 読み込み順: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - .env パーサを実装（コメント、export プレフィックス、クォート、バックスラッシュエスケープ、行内コメント取り扱い等に対応）。
  - Settings クラスを提供し、必要な環境変数をプロパティ経由で取得:
    - J-Quants / kabu ステーション / LINE Messaging / DB パス（DuckDB/SQLite）/監視設定（pid, kill flag, CPU/メモリ/ディスク閾値）等をカバー。
  - バリデーション: KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL（DEBUG/INFO/...）の検査。
  - 必須変数未設定時は明示的に ValueError を送出する _require を実装。

- AI モジュール（src/kabusys/ai/**）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約し、銘柄ごとにニュースをまとめて OpenAI（gpt-4o-mini、JSON mode）へ送信してセンチメント（-1.0〜1.0）を算出。
    - タイムウィンドウ計算（calc_news_window）: 前日 15:00 JST ～ 当日 08:30 JST 相当の UTC 範囲を返却。
    - バッチ処理（1 API コールあたり最大 20 銘柄）、1 銘柄あたり記事上限（最新 10 件、最大 3000 文字でトリム）。
    - 再試行ロジック: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ（設定値で上限制御）。
    - レスポンス検証ロジック: JSON 抽出、"results" の存在/型チェック、コード照合、スコア数値チェック、±1.0 でクリップ。
    - 部分失敗対策: 成功した銘柄コードのみを DELETE→INSERT で置換（部分失敗時に既存スコア保護）。DuckDB の executemany 空リスト問題に配慮。
    - フェイルセーフ: API エラー時はスキップして継続（例外を投げず処理を継続する設計）。
    - テスト性: OpenAI 呼び出し部分は内部関数 _call_openai_api を用意しており、ユニットテストでモック可能。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - LLM 呼び出しは gpt-4o-mini（JSON mode）を使用。記事が無ければ LLM 呼び出しは行わずマクロスコアは 0.0。
    - API の再試行はニュース NLP と同様の方針（RateLimit, timeout, 5xx のリトライ、最大リトライ回数）。
    - 計算結果を market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で書き込み。DB 書き込み失敗時には ROLLBACK を試行して上位へ例外を伝播。
    - ルックアヘッドバイアス回避: date 引数の未満データのみ参照、datetime.today() を参照しない設計。

- Research（src/kabusys/research/**）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン・200 日 MA 乖離）、Volatility（20 日 ATR、ATR 相対値）、Liquidity（20 日平均売買代金、出来高比率）、Value（PER、ROE）等の計算関数を実装。
    - DuckDB を用いた SQL ベースの計算を実現し、prices_daily / raw_financials のみ参照。外部 API にアクセスしない安全な設計。
    - データ不足の場合の None 扱い、200 日未満等の判定を実装。
  - 特徴量探索 / 統計（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）: 複数ホライズン（デフォルト [1,5,21]）を同一クエリで取得。horizons の検証あり（1〜252 の整数）。
    - IC（Information Coefficient）計算（calc_ic）: Spearman の rank 相関を実装。並順位の平均ランク処理、必要レコード数が不足する場合は None を返す。
    - rank ユーティリティ: ties の処理（同順位は平均ランク）、丸めで浮動小数点誤差対策。
    - factor_summary: 指定カラムの count/mean/std/min/max/median を計算する純 Python 実装（外部依存なし）。

- Data プラットフォーム（src/kabusys/data/**）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを基に営業日の判定 / 前後営業日取得 / 期間内営業日列挙 / SQ 日判定の API を提供。
    - DB 登録がない日や NULL がある場合は曜日ベース（土日非営業）でフォールバックする一貫したロジック。
    - next_trading_day / prev_trading_day は最大探索日数を設定して無限ループを防止。
    - calendar_update_job: J-Quants API（jquants_client 経由）から差分取得し冪等に保存。バックフィル期間や健全性チェック（遠すぎる last_date はスキップ）を実装。
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - ETLResult dataclass を実装して ETL 実行の集計・監査情報（取得件数・保存件数・品質問題・エラー等）を保持。to_dict でシリアライズ可能。
    - 差分更新・バックフィル・品質チェック（quality モジュール）・jquants_client を使った保存を行う設計方針を文書化。
    - 内部ユーティリティ: テーブル存在判定、最大日付取得などを実装。
  - etl モジュールで ETLResult を再エクスポート（src/kabusys/data/etl.py）。

Other
- モジュールの公開（__all__）整理:
  - ai/__init__.py: score_news を公開。
  - research/__init__.py: 主要な計算関数と zscore_normalize を再エクスポート。

Design / Safety / Testability notes（設計上の重要点）
- ルックアヘッドバイアス防止: AI・研究モジュールともに datetime.today()/date.today() を直接参照しない設計（target_date を明示的に受け取る）。
- フェイルセーフ: OpenAI 呼び出し失敗時はスコアをゼロにフォールバックしたり、そのチャンクをスキップして処理継続する方針。致命的な DB 書き込み失敗は例外で伝播。
- 冪等性とトランザクション: market_regime / ai_scores などの DB 書き込みは冪等化（DELETE してから INSERT、BEGIN/COMMIT/ROLLBACK 管理）。
- テスト容易性: OpenAI 呼び出し部分（_call_openai_api）を一箇所に抽象化しており、ユニットテストでパッチ可能。
- DuckDB 互換性配慮: executemany の空リスト制約や日付型ハンドリングへの注意がコード内に明記されている。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / Known limitations
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY に依存。未設定時は ValueError を送出する箇所があるため、運用時には環境変数設定が必要。
- 一部機能は外部クライアント（jquants_client 等）に依存。これらのクライアント実装・API レスポンス形式により挙動が変わる可能性がある。
- 現バージョンでは PBR・配当利回りなどのバリューファクターは未実装（calc_value に注記あり）。

---

今後の提案（推奨）
- ユニットテスト/統合テストの追加（特に OpenAI クライアントや DuckDB 書き込みのモックを含む）。
- リリースノートに具体的な API 例や .env.example のサンプル追記（運用者向けドキュメント）。
- エラーメトリクス収集（Sentry 等）と監視アラートの整備。