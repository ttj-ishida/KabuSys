# Changelog

すべての重要な変更は Keep a Changelog のフォーマットに従って記載します。  
このファイルはコードベースから推測した初期リリースの機能・設計決定・フェイルセーフ等をまとめたものです。

※日付はコード内の参照や現在日付を基に推定しています。

## [Unreleased]

### Added
- （今後のリリース向けの未反映の変更をここに記載）

---

## [0.1.0] - 2026-03-28

初回公開想定リリース。日本株自動売買・データ基盤・リサーチ・AI解析のコア機能を実装。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。公開 API として data, research, ai, execution, strategy, monitoring などを想定（__all__ に定義）。
  - パッケージバージョンを `0.1.0` に設定。

- 設定管理
  - 環境変数 / .env ファイル読み込みモジュールを追加（kabusys.config）。
    - 自動的にプロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を読み込む仕組みを実装。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - 環境変数自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を実装。
    - .env パーサで `export KEY=val`、クォート（シングル/ダブル）内のバックスラッシュエスケープ、インラインコメントの取り扱い等に対応。
    - Settings クラスを提供し、必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）をプロパティ経由で取得・バリデート。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL のバリデーションを実装。
    - データベースパスの既定値（DuckDB: data/kabusys.duckdb、SQLite: data/monitoring.db）を提供。

- データ基盤（Data）
  - market_calendar（JPXカレンダー）管理モジュールを実装（kabusys.data.calendar_management）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定APIを提供。
    - DB にカレンダーがない場合は曜日ベースでフォールバックする堅牢な設計。
    - calendar_update_job：J-Quants から差分取得して market_calendar を冪等的に更新するバッチ処理を実装。バックフィル、健全性チェック（未来日が不正に遠い場合はスキップ）を組み込み。
  - ETL パイプライン関連（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラス（target_date, fetch/save カウント、品質チェック情報、エラー一覧）を実装。to_dict によるシリアライズを提供。
    - テーブル存在チェックや最大日付取得などのユーティリティ関数を実装。
    - jquants_client 経由で差分取得→保存→品質チェックのワークフローを想定した設計。

- AI モジュール
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を算出。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST 相当／UTC換算）を calc_news_window で提供。
    - 1チャンクあたりのバッチ処理（デフォルト 20 銘柄）、1銘柄当たりの記事数上限・文字数上限（トリム）などのトークン肥大対策を実装。
    - API 呼び出しは JSON Mode を利用し、レスポンスを厳密に検証（results 配列、code/score 指定、未知コード無視、数値チェック、±1.0 でクリップ）。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライを実装。失敗時は対象チャンクをスキップして処理継続（フェイルセーフ）。
    - スコア書き込みは部分失敗を考慮して、取得済みコードのみ DELETE → INSERT（トランザクション内）で置換する実装。
    - テストしやすさのため _call_openai_api の差し替え（patch）を想定。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - ma200_ratio 計算は target_date 未満のデータのみを使用してルックアヘッドを防止。
    - マクロ記事抽出は定義済みマクロキーワード群でフィルタ（最大 20 件）。
    - OpenAI 呼び出し失敗時は macro_sentiment を 0.0 にフォールバック（フェイルセーフ）。
    - レジームを market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）するトランザクション処理を実装。
    - API 呼び出しについてもテスト用差し替えを想定。

- リサーチ（Research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATRなど）、Value（PER, ROE）を DuckDB 上の SQL と Python 組合せで実装。
    - データ不足時は None を返す等の堅牢な挙動。
    - 出力は (date, code) をキーにした辞書リストとして統一。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン calc_forward_returns（デフォルト horizons=[1,5,21]）を実装。ホライズンのバリデーションあり。
    - IC（Information Coefficient）計算（スピアマンランク相関）を実装。データ不足（有効レコード < 3）の場合は None。
    - rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）などのユーティリティを実装。
  - zscore_normalize 等の基本ユーティリティを data.stats 経由で公開。

### Changed
- ドキュメント指向の設計方針を反映
  - 主要な分析/スコアリング関数は datetime.today() / date.today() を参照せず、引数 target_date を必須にしてルックアヘッドバイアス回避を徹底。
  - DuckDB を前提とした SQL の記述と、実行互換性（executemany 空リスト回避）への配慮を導入。

### Fixed / Reliability improvements
- トランザクションとロールバック
  - market_regime / ai_scores 等の DB 書き込みで BEGIN/COMMIT/ROLLBACK を用いた冪等・安全書き込みを実装。ROLLBACK の失敗もログに記録して上位に例外を再送出する設計。

- API 呼び出しの堅牢化
  - OpenAI API 呼び出しでの例外分類（429, ネットワーク, タイムアウト, 5xx, その他）に応じたリトライ戦略とログ出力を用意。
  - JSON レスポンスのパース失敗時は復元（最外の {} 抽出）を試み、失敗した場合はスキップして継続。

### Security
- 環境変数の保護
  - .env のロード時に既存の OS 環境変数を保護（protected set）する挙動を実装。
  - 自動ロードを無効化する環境フラグを用意し、テスト/CIでの漏洩リスクを軽減可能。

### Internal
- テストしやすさを考慮した設計
  - _call_openai_api 等の内部関数をテスト用に差し替え可能にしており、外部 API 依存のテスト容易性を確保。
- ロギング
  - 各処理で詳細な logger 出力を追加。失敗時には context を含む警告／例外ログを残すように実装。

---

## 既知の制限（推測）
- 実行・発注（execution）、ストラテジー（strategy）、モニタリング（monitoring）に関する具象的な実装はソース内には見当たらないため、これらは別モジュールか今後の実装を想定。
- 外部 API（J-Quants、kabuステーション、OpenAI）のクライアント実装は別モジュール（jquants_client 等）に依存している想定。
- PBR・配当利回りなど一部バリューファクターは未実装（コメントで言及）。

---

この CHANGELOG はコードベースの内容からの推測に基づき作成しています。実際のリリース履歴や日付・カテゴリはプロジェクトの運用方針に合わせて調整してください。変更点の詳細説明（関数や定数名）はドキュメントコメントを参照することで補完できます。