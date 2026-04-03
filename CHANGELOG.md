# CHANGELOG

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

履歴に記載されていない変更は存在するとみなさないでください。

## [Unreleased]

## [0.1.0] - 2026-04-03
初回リリース — 基本機能の実装と主要モジュールを公開。

### 追加 (Added)
- パッケージ全体
  - パッケージ名: kabusys。バージョンを `__version__ = "0.1.0"` に設定。
  - public API: data, strategy, execution, monitoring を __all__ で公開準備。

- 設定管理 (src/kabusys/config.py)
  - Settings クラスを実装し、環境変数経由での設定取得を提供。
  - .env 自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml から探索）。
  - .env と .env.local の読み込み順序を実装（OS 環境変数を保護、.env.local は上書き可能）。
  - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
  - .env のパースを堅牢化:
    - export プレフィックス対応、クォート内のエスケープ処理、インラインコメント処理などに対応。
  - 各種設定プロパティを定義（J-Quants, kabu API, LINE, DB パス, 監視閾値, ログ/環境種別判定 等）。
  - 環境値のバリデーション（KABUSYS_ENV・LOG_LEVEL）と便利なフラグプロパティ（is_live, is_paper, is_dev）を実装。

- AI（自然言語処理） (src/kabusys/ai)
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を入力に OpenAI (gpt-4o-mini) を用いた銘柄別ニュースセンチメント評価を実装。
    - タイムウィンドウ（前日15:00 JST〜当日08:30 JST）計算 (`calc_news_window`)。
    - 銘柄毎の最新記事を集約（記事数・文字数上限でトリム）し、最大20銘柄ずつバッチ送信。
    - JSON Mode を利用した厳密な JSON 出力期待、レスポンスのバリデーションを実装。
    - エラー耐性: 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ。
    - スコアを ±1.0 にクリップし、取得済み銘柄のみ ai_scores テーブルに置換（DELETE→INSERT、部分失敗時に既存値を保護）。
    - テスト容易性のため OpenAI 呼び出し関数を差し替え可能に実装。

  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日 MA 乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロキーワードで raw_news をフィルタ、OpenAI で macro_sentiment を算出（記事がなければ呼出し省略）。
    - レジームスコア合成ルールと閾値を実装、market_regime テーブルへ冪等（BEGIN/DELETE/INSERT/COMMIT）で書き込み。
    - API 呼び出しのリトライ/バックオフ、フェイルセーフ（API 失敗時は macro_sentiment=0.0）。
    - ルックアヘッドバイアス防止のため date 引数を明示的に用いる設計（datetime.today() を参照しない）。

- データ基盤（src/kabusys/data）
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - 差分更新・バックフィル・品質チェックの方針に基づく ETLResult dataclass を実装。
    - DuckDB を用いたテーブル存在チェック、最大日付取得等のユーティリティを実装する土台を追加。
    - 結果の to_dict メソッドで品質問題を辞書化して出力可能に。
  - etl モジュール公開インターフェース（src/kabusys/data/etl.py）で ETLResult を再エクスポート。
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダーの夜間バッチ更新 job 実装（calendar_update_job）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを実装。
    - market_calendar が未取得の場合の曜日ベースフォールバック、DB 値優先の一貫した判定ロジック。
    - バックフィル、健全性チェック、最大探索日数（_MAX_SEARCH_DAYS）など安全パラメータを導入。
    - J-Quants クライアント呼び出しと保存処理を想定した実装（jq.fetch_market_calendar / jq.save_market_calendar を利用）。

- リサーチ / ファクター（src/kabusys/research）
  - factor_research モジュール（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金/出来高比）、バリュー（PER/ROE）の計算関数を実装。
    - DuckDB を用いた SQL ベースの集計で、データ不足時は None を返す設計。
    - 関数群: calc_momentum, calc_volatility, calc_value を提供。
  - feature_exploration モジュール（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、ランク変換ユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - pandas に依存せず標準ライブラリのみで実装。
  - research パッケージ初期エクスポートを用意（calc_momentum 等と zscore_normalize の再エクスポート）。

### 変更 (Changed)
- 設計上の方針文書的変更をコードへ反映:
  - すべての時刻処理はルックアヘッドバイアスを避けるため target_date ベースで実行。datetime.today()/date.today() を参照しない実装を原則とする箇所を明示。
  - DuckDB の互換性考慮（executemany の空リスト禁止等）を反映した実装。

### 修正 (Fixed)
- 初期バージョンのため特定の「バグ修正」は無し。ただし堅牢性のため下記の耐障害設計を導入：
  - OpenAI 呼び出しに対するリトライ/バックオフと失敗時のフェイルセーフ（ゼロ値フォールバック）を導入。
  - DB 書き込みは冪等化（DELETE→INSERT）とトランザクション管理（BEGIN/COMMIT/ROLLBACK）で保護。
  - .env 読み込みでファイルオープン失敗時に warnings.warn を出すようにしてプロセスが継続できるようにした。

### セキュリティ (Security)
- OpenAI API キーや Kabusys の機密情報は環境変数経由で取得し、Settings によるアクセス制御を提供。デフォルトでキー未設定時には例外を投げる実装（明示的な管理を促進）。

### 既知の制約 / 注記 (Known issues / Notes)
- OpenAI 連携は gpt-4o-mini を前提とした実装。API のレスポンス形式/SDK の変化に伴い将来的な調整が必要になる可能性あり（status_code の取扱い等は SDK 互換を考慮）。
- DuckDB バインドの挙動（リストバインド等）はバージョン差異に依存するため、互換性を考慮した実装（個別 DELETE の executemany 等）を採用している。
- calendar_update_job 等は J-Quants クライアント（kabusys.data.jquants_client）との連携を想定しているため、実行には該当クライアント実装・資格情報が必要。
- 現段階では PBR・配当利回り等の一部バリューファクターは未実装。

---

今後のリリースでは以下を想定:
- strategy / execution / monitoring の実装反映（実売買ロジック、発注エンジン・監視プロセスの実装）
- 単体テストおよび統合テストの追加、CI 設定
- ドキュメント強化（各モジュールの使用例・API リファレンス）
- 性能チューニング（大規模データセット向け最適化）、及びエラーハンドリングの拡充

（以上）