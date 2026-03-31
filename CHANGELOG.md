# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
以下の内容は提供されたコードベースの実装内容から推測・要約したものであり、実際のコミット履歴ではなくコードの機能説明をもとにした初期リリースノートです。

## [0.1.0] - 2026-03-31
初回リリース。日本株の自動売買／データ基盤向けユーティリティ群をまとめたパッケージを提供します。

### Added
- パッケージ初期化
  - kabusys パッケージエントリポイント（src/kabusys/__init__.py）。公開モジュール: data, strategy, execution, monitoring。
  - バージョン番号: 0.1.0。

- 環境設定管理
  - 環境変数読み込み・管理モジュール（src/kabusys/config.py）を追加。
    - .env と .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動ロードする機能。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
    - 高度な .env パーサ（export 形式、引用符内のエスケープ、インラインコメントの扱い等に対応）。
    - Settings クラス: J-Quants / kabu API / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル等のプロパティを提供。必須変数未設定時は ValueError を送出するバリデーションを実装。

- AI モジュール（OpenAI 統合）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）:
    - score_news(conn, target_date, api_key=None): raw_news / news_symbols を集約して OpenAI (gpt-4o-mini) にバッチで問い合わせ、銘柄ごとの ai_score を ai_scores テーブルへ書き込む。
    - タイムウィンドウ計算（JST基準の前日15:00〜当日08:30 を UTC に換算）。
    - チャンク処理（_BATCH_SIZE=20）・記事トリム（文字数/記事数上限）・JSON Mode を用いた堅牢なレスポンス処理。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ）およびフェイルセーフ動作（失敗時はスキップして他銘柄処理を継続）。
    - レスポンスのバリデーションとスコアクリップ（±1.0）。
    - DuckDB に対する冪等書き込み（DELETE→INSERT, executemany 用の空チェック）。

  - レジーム判定（src/kabusys/ai/regime_detector.py）:
    - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日 MA 乖離とマクロニュース（news_nlp のウィンドウ集計）を組み合わせて市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ冪等書き込み。
    - OpenAI 呼び出しは独立実装でモジュール結合を避ける設計。
    - API エラー時は macro_sentiment=0.0 のフォールバック（フェイルセーフ）。
    - ルックアヘッドバイアスを避けるため、target_date 未満のみを参照する設計。

  - ai パッケージの公開: score_news を __all__ で公開。

- データプラットフォームユーティリティ
  - カレンダー管理（src/kabusys/data/calendar_management.py）:
    - JPX カレンダー更新ジョブ calendar_update_job(conn, lookahead_days)（J-Quants から差分取得して market_calendar を更新）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定関数。
    - market_calendar が未登録の場合は曜日ベースのフォールバック動作を提供。
    - 最大探索日数制限やバックフィル等の安全機構。

  - ETL / パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）:
    - ETLResult データクラスを定義（取得件数・保存件数・品質チェック結果・エラーメッセージ等を格納）。
    - 差分取得・バックフィル・品質チェックを想定した設計（jquants_client 経由での保存、品質チェックは呼び出し元が対処）。
    - etl モジュールは ETLResult を再エクスポート。

- Research（解析）モジュール
  - ファクター計算（src/kabusys/research/factor_research.py）:
    - calc_momentum(conn, target_date): mom_1m / mom_3m / mom_6m / ma200_dev を計算（200日データ不足時は None）。
    - calc_volatility(conn, target_date): atr_20 / atr_pct / avg_turnover / volume_ratio 等の計算（欠損ハンドリング）。
    - calc_value(conn, target_date): raw_financials から最新財務を取得して PER / ROE を計算。
    - DuckDB 上の SQL ウィンドウ関数を活用した実装。

  - 特徴量探索（src/kabusys/research/feature_exploration.py）:
    - calc_forward_returns(conn, target_date, horizons): 将来リターンの計算（複数ホライズン対応、ホライズン検証）。
    - calc_ic: スピアマンのランク相関（IC）計算（結合・欠損除外・最小サンプルチェック）。
    - rank: 同順位は平均ランクにするランク付けユーティリティ（丸め対策あり）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
  - research パッケージの __all__ に主要関数を公開。

- その他
  - DuckDB を前提とした各モジュール実装（関数は DuckDB 接続を受け取る設計）。
  - OpenAI SDK（OpenAI クライアント）を使用する箇所でテスト容易性を考慮し、内部呼び出し関数を差し替え可能に実装（unittest.mock.patch 想定）。
  - ロギングを各モジュールに追加して情報/警告/例外時の出力を整備。

### Changed
- 設計上のキー方針（全体）:
  - ルックアヘッドバイアス回避の徹底: datetime.today()/date.today() をスコープ内で直接参照しない（関数引数で target_date を受ける設計）。
  - DB 書き込みは冪等性を重視（既存行を削除してから挿入する、トランザクションで COMMIT/ROLLBACK）。
  - API 呼び出しの失敗は基本的に例外暴露ではなくフェイルセーフ（部分失敗を許容して他処理継続）する方針。

### Fixed / Robustness
- .env パーサの堅牢化:
  - export 先頭表記、シングル/ダブルクォート内のバックスラッシュエスケープ、クォート無しでのコメント扱い等を実装し、一般的な .env フォーマットに対応。
  - プロジェクトルート探索を __file__ ベースで行い、CWD に依存しない自動読み込み。

- OpenAI 呼び出しとレスポンス処理の堅牢化:
  - 429/ネットワーク/タイムアウト/5xx を対象にリトライ（指数バックオフ）を実装。
  - レスポンス JSON のパース失敗時に外側の大括弧を抽出して復元する等の寛容な処理を追加（news_nlp）。
  - レスポンスのバリデーションで未知のコードや非数値スコアを無視し、影響範囲を最小化。
  - API キー未設定時は早期に ValueError を返すことで呼び出し側に明示。

- DB 書き込みの安全性:
  - DuckDB の executemany が空リストを受け付けない点への対応（空チェック）。
  - トランザクション失敗時に ROLLBACK を試行し、ROLLBACK 自体の失敗はログで警告（例外は再送出）。

### Security
- 必須機密情報の明示:
  - OpenAI API キー、J-Quants リフレッシュトークン、Kabu API パスワード、Slack トークン/チャンネル ID などは Settings 経由で必須チェックを行い、未設定時に ValueError を送出することでミスコンフィグに早期に気づけるようにしています。

### Notes / Known limitations
- 外部依存:
  - OpenAI モデル「gpt-4o-mini」を想定して実装。実行時に API 仕様やモデル名の差異がある場合、適宜調整が必要です。
  - J-Quants / kabu_station 用クライアント（jquants_client 等）はモジュール参照を行っているが、実ランタイムでの接続/認証の実装やテストは別途必要です。

- フェイルセーフ動作の影響:
  - AI 関連処理は API 失敗時に「スコア 0.0」や「スキップ」で継続するため、部分的にスコアが欠損しても他処理は続行します。運用方針に応じて失敗時の扱い（再試行ポリシーの変更やアラート発報）を検討してください。

- テスト容易性:
  - OpenAI 呼び出し部は内部関数をパッチしてモック可能なように設計されています。ユニットテストではこれらを差し替えて API 実呼び出しを回避してください。

---

以上がコードベースから推測した初期リリースの CHANGELOG です。必要であれば、各セクションをより詳細な項目（関数単位の変更履歴や想定される実行例、既知の改善点）に分解して追記できます。どのレベルの詳述を希望しますか？