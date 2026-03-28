# Changelog

すべての重要な変更はこのファイルに記録します。  
このファイルは「Keep a Changelog」の慣習に従って記載しています。  

## [0.1.0] - 2026-03-28

初回公開リリース — KabuSys: 日本株自動売買システムの基礎コンポーネントを実装。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージを追加。バージョンは `0.1.0`。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルまたは OS 環境変数から設定を自動読み込みする機能を実装。
    - プロジェクトルート検出は `.git` または `pyproject.toml` を基準に行い、CWD に依存しない実装。
    - 読み込み順: OS 環境変数 > .env.local > .env。
    - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能（テスト用）。
  - .env パーサは次の挙動に対応:
    - `export KEY=val` 形式サポート、クォート付き値のバックスラッシュエスケープ処理、インラインコメントの扱い。
  - Settings クラスを導入し、アプリケーションで利用する各種設定をプロパティとして提供:
    - J-Quants / kabu API / Slack / データベースパス（DuckDB, SQLite）/ 環境（development/paper_trading/live）/ ログレベル等。
    - 必須設定未指定時は ValueError を送出する `_require` を採用。
    - env/log_level の入力検証とヘルパー（is_live/is_paper/is_dev）を提供。

- AI モジュール (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメント（ai_score）を ai_scores テーブルへ書き込み。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を `calc_news_window` で提供。
    - バッチサイズ、記事数・文字数制限、JSON Mode を用いたレスポンス処理、レスポンス検証、スコアの ±1.0 クリップを実装。
    - API エラー（429/ネットワーク/タイムアウト/5xx）は指数バックオフでリトライ。失敗時はロギングしてスキップ（フェイルセーフ）。
    - テスト用に `_call_openai_api` をモック可能に設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - マクロキーワードによる記事フィルタ、OpenAI（gpt-4o-mini）呼び出し、リトライ/バックオフ、レスポンスパース、スコア合成、閾値判定を実装。
    - DB への書き込みは冪等に行う（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
    - API 呼び出し失敗時は macro_sentiment=0.0 として継続するフェイルセーフ設計。
    - テスト用に `_call_openai_api` を差し替え可能。

- データ関連 (kabusys.data)
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを基に営業日判定・SQ 判定を行うユーティリティを提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にデータがない場合は曜日ベース（平日を営業日）でフォールバック。
    - calendar_update_job: J-Quants からの差分取得 → 保存（バックフィルや健全性チェックあり）。
  - ETL インターフェース（kabusys.data.etl / pipeline）
    - ETLResult データクラスを公開。ETL 実行結果（取得数、保存数、品質問題、エラー等）を集約。
    - pipeline モジュールに差分更新・バックフィル・品質チェック連携などの基盤ユーティリティを実装（J-Quants クライアント経由でデータ取得・保存を想定）。
    - DuckDB を用いたテーブル存在確認や最大日付取得のユーティリティ等を提供。
    - ETL の品質チェックは致命的エラーを検出しても処理自体は継続し、呼び出し元が対応を決定できる設計。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research:
    - Momentum（1M/3M/6M リターン・200日 MA 乖離）、Volatility（20日 ATR、相対 ATR）、Value（PER・ROE）、Liquidity（20日平均売買代金・出来高比）などのファクター計算を実装。
    - DuckDB SQL を活用し、prices_daily / raw_financials のみ参照する設計（本番口座や発注APIには接触しない）。
    - データ不足時は None を返す挙動。
  - feature_exploration:
    - 将来リターン計算（複数ホライズン／デフォルト [1,5,21]）、IC（Spearmanランク相関）計算、ファクター統計サマリ（count/mean/std/min/max/median）、ランク付けユーティリティを実装。
    - 外部ライブラリに依存せず、標準ライブラリのみで実装。

### 改良 (Changed)
- 実装面の設計方針が明確化
  - 主要なモジュールで datetime.today()/date.today() を直接参照しないことでルックアヘッドバイアスを防止する設計を採用。
  - DuckDB 互換性（executemany の空リスト不可等）を考慮した実装。
  - OpenAI 呼び出し処理はモジュール間でプライベート関数を共有せず、テスト容易性のため差し替え可能にデザイン。

### 修正 (Fixed)
- （初回リリースのため特定のバグ修正履歴はなし）

### 注意事項 / 互換性
- 外部依存:
  - duckdb および openai SDK に依存。OpenAI は gpt-4o-mini（JSON mode）利用を想定。
- DB スキーマ:
  - このリリースは prices_daily / raw_news / news_symbols / ai_scores / market_calendar / raw_financials 等のテーブルが存在することを前提とする関数が多数含まれます。実行前に必要なスキーマを用意してください。
- テスト:
  - OpenAI 呼び出し部分は内部の `_call_openai_api` を unittest.mock.patch 等で差し替えることによりユニットテストが可能です。
- フェイルセーフ:
  - 外部 API 失敗時は多くの処理がスキップまたは中立値にフォールバックして継続します。運用時はログ監視・再実行戦略を検討してください。

---

今後のリリース予定例:
- 0.2.0: 発注（execution）/モニタリング（monitoring）モジュールの実装、より厳密なデータ品質検査、CI テストの追加。
- 1.0.0: 安定 API とドキュメント整備、後方互換性の確立。

（詳しい実装コメントは各モジュールの docstring を参照してください。）