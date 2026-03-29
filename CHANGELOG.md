# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
このファイルはコードベース（src/kabusys 以下）から推測して生成した初期の変更履歴です。

## [Unreleased]

（現時点のコードは初期版として 0.1.0 を想定しています。以降の変更はここへ追記してください）

---

## [0.1.0] - 初期リリース (推定)

公開日: 未設定

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期モジュール群を追加。バージョンは `0.1.0`。
  - __all__ により "data", "strategy", "execution", "monitoring" を公開。

- 設定・環境変数管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルートを .git または pyproject.toml を基準に探索して自動ロード（CWD 非依存）。
  - .env の各種形式に対応：
    - 行コメント、先頭の "export " プレフィックス対応
    - シングル/ダブルクォート内でのバックスラッシュエスケープ対応
    - クォート無しの行でのインラインコメント解析（直前が空白/タブの場合のみ）
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - OS 環境変数保護（protected）を考慮した上書きロジック。
  - Settings クラスを提供し、主要設定プロパティを公開（J-Quants, kabu API, Slack, DBパス, 環境種別・ログレベル等）。
  - KABUSYS_ENV / LOG_LEVEL のバリデーションを実装。

- AI モジュール (`kabusys.ai`)
  - news_nlp
    - ニュース記事を銘柄ごとに集約して OpenAI（gpt-4o-mini）でセンチメント評価を行い、`ai_scores` テーブルへ書き込む `score_news` を実装。
    - タイムウィンドウ定義（前日15:00 JST 〜 当日08:30 JST を UTC に変換）と記事集約ロジックを実装。
    - バッチ処理（最大 20 銘柄 / API コール）、1 銘柄あたりの記事数・文字数上限を実装。
    - OpenAI 呼び出しのリトライ（429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ）とレスポンス検証（JSON 抽出・スコア数値チェック）を実装。
    - DuckDB に対する冪等書き込み（DELETE → INSERT）を実装。部分失敗時に既存データを保護する設計。
    - テスト容易性のため `_call_openai_api` を patch 可能に設計。

  - regime_detector
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する `score_regime` を実装。
    - マクロニュース取得は `news_nlp.calc_news_window` を利用し、キーワードベースでタイトルを抽出。
    - OpenAI 呼び出しに対する堅牢なリトライ・フェイルセーフ実装（最終的に macro_sentiment=0.0 にフォールバック）。
    - 結果を `market_regime` テーブルへ冪等的に書き込むトランザクション処理を実装。
    - ルックアヘッドバイアス防止の設計（内部で datetime.today()/date.today() を参照しない、クエリで target_date 未満条件を付与）。

- データモジュール (`kabusys.data`)
  - calendar_management
    - JPX カレンダー管理（market_calendar）用ユーティリティを実装。
    - 営業日判定（is_trading_day）、次/前営業日取得（next_trading_day / prev_trading_day）、期間内営業日取得（get_trading_days）、SQ日判定（is_sq_day）を実装。
    - DB 登録がない場合は曜日（土日）ベースでフォールバックする挙動。
    - calendar_update_job により J-Quants から差分取得して冪等保存するバッチ処理を実装。バックフィル・健全性チェックを実装。
  - pipeline / ETL
    - ETL の公開インターフェースとして `ETLResult` を追加（データクラス）。
    - ETLResult は取得数・保存数・品質問題・エラー一覧を保持し、辞書化メソッドを提供。
    - ETL 補助ユーティリティ（テーブル存在チェック、最大日付取得など）を実装。
    - 差分取得・バックフィル・品質チェックの設計方針を反映（コードコメント）。

- 研究・ファクター分析モジュール (`kabusys.research`)
  - factor_research
    - Momentum（1M/3M/6M リターン、ma200乖離）、Volatility（20日 ATR、相対ATR、平均売買代金、出来高比率）、Value（PER、ROE）などのファクター計算関数を実装。
    - DuckDB を用いた SQL ベースの計算を実装し、返り値は (date, code) ベースの辞書リスト。
    - データ不足時の None ハンドリングやログ出力を実装。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（Spearman ランク相関）計算（calc_ic）、ランク変換 (rank)、統計サマリー (factor_summary) を実装。
    - pandas 等の外部ライブラリに依存しない純標準ライブラリ実装。
  - research/__init__.py で主要関数を再エクスポート。

- 共通技術選定
  - データベースは DuckDB を利用する想定。SQL と Python の組合せで分析・ETL を進める設計。
  - OpenAI SDK（OpenAI クライアント）を利用。テスト容易性のため呼び出し箇所を差し替え可能に設計。

### 変更 (Changed)
- （初期リリースにつき該当なし）

### 修正 (Fixed)
- OpenAI 呼び出しや JSON パースの失敗について、例外をそのまま投げない（フェイルセーフ）挙動を採用。API 異常時はログ出力して該当処理をスキップまたはゼロ値で継続する設計。
- DuckDB の executemany に対する互換性問題（空リスト不可）を考慮したコードを実装。

### セキュリティ (Security)
- 環境変数自動ロードはデフォルトで有効だが、`KABUSYS_DISABLE_AUTO_ENV_LOAD` によって明示的に無効化可能。
- .env 自動ロード時に OS 環境変数を上書きしないデフォルト動作を採用。また、上書き動作時も protected キー集合は維持される。

### 設計注記 / ドキュメント化された挙動
- ルックアヘッドバイアス防止：AI スコア計算・レジーム判定・ETL 等の主要処理はすべて target_date を受け取り内部で date.today() を参照しないよう設計されている。
- DB 書き込みは可能な限り冪等（DELETE→INSERT、ON CONFLICT 想定）およびトランザクション（BEGIN/COMMIT/ROLLBACK）で保護。
- テスト容易性を念頭に置いた実装（OpenAI 呼び出し部分の差し替え等）。

---

今後のリリースノート（例）
- Unreleased: 改善や新機能（strategy / execution / monitoring の実装詳細追加、テストカバレッジ向上、CLI/API の追加など）
- 0.1.x: バグ修正、OpenAI レスポンス検証の強化、ETL の並列化 など

（以上）