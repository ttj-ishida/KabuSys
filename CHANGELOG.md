CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

[Unreleased]
-------------

（なし）

[0.1.0] - 2026-03-29
-------------------

Added
- 初回リリース: KabuSys — 日本株自動売買システムのコアライブラリを追加。
  - パッケージ公開情報
    - バージョン: 0.1.0
    - top-level エクスポート: data, strategy, execution, monitoring（パッケージの主要サブパッケージを公開）
- 環境設定 / 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート検出ロジック: .git または pyproject.toml を起点に探索（CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - OS 環境変数の上書きを防ぐための protected キーセットを採用。
  - .env パーサーの強化:
    - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い（クォート有無でのコメント判定）などに対応。
  - Settings クラスを提供（J-Quants / kabuステーション / Slack / データベースパス / 環境モード / ログレベル等）。
    - 必須変数未設定時は ValueError を送出する _require ユーティリティ実装。
    - env, log_level の値検証（許容値セットによる検査）。
    - is_live / is_paper / is_dev の簡易判定プロパティ。

- ニュース NLP / 市場レジーム判定 (kabusys.ai)
  - news_nlp.score_news:
    - raw_news と news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）の JSON Mode を使ってセンチメントスコアを算出して ai_scores テーブルへ保存する機能。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）対応。calc_news_window 提供。
    - チャンク処理（最大 20 銘柄／API 呼び出し）、記事・文字数トリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフでのリトライ。
    - レスポンスの厳密なバリデーション: JSON 抽出（余計な前後テキストの補正含む）、"results" リストの検証、コード名の正規化、スコアの有限性検査、±1.0 でクリップ。
    - 部分失敗時に既存データを保護するため、取得済みコードのみ DELETE → INSERT で置換（DuckDB 互換性を考慮した executemany の扱い）。
  - regime_detector.score_regime:
    - ETF 1321（Nikkei 225 連動 ETF）の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して market_regime テーブルへ保存。
    - マクロ記事抽出（キーワードベース）、OpenAI 呼び出し（gpt-4o-mini）による macro_sentiment 評価、スコア合成とラベリング（bull/neutral/bear）。
    - API 呼び出しのリトライ・フォールバック（失敗時 macro_sentiment=0.0）や JSON パース失敗の耐性。
  - テスト容易性のため、OpenAI 呼び出しを行う内部関数（_call_openai_api）をモック差替え可能に実装。

- データプラットフォーム / ETL (kabusys.data)
  - pipeline.ETLResult: ETL 実行結果を表す dataclass をエクスポート（to_dict により品質問題をシリアライズ可能）。
  - ETL 設計:
    - 差分更新・バックフィルの方針を組み込んだ処理設計（最終取得日のチェック、backfill_days による再取得）。
    - 品質チェック（quality モジュール）との連携インタフェース（品質問題は収集して処理継続）。
    - DuckDB 上での最大日付取得やテーブル存在判定ユーティリティを提供。
  - calendar_management:
    - JPX カレンダー管理: market_calendar テーブルを用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB にカレンダーデータがない場合は曜日ベースのフォールバック（週末を非営業日扱い）。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新（バックフィル、健全性チェック、保存件数を返す）。
    - 最大探索範囲（_MAX_SEARCH_DAYS）やバックフィル日数などの安全策を組み込み。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、ma200 乖離などの算出（prices_daily のウィンドウ集計・不足データ時の None 処理）。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率などの算出。
    - calc_value: raw_financials からの EPS/ROE を用いた PER/ROE の計算（最新財務レコードの選択ロジック含む）。
    - DuckDB のウィンドウ関数を活用した高効率実装。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト: [1,5,21]）の将来リターンを一括取得する汎用クエリ。
    - calc_ic: ファクター値と将来リターン間の Spearman ランク相関（IC）を実装。データ不足時は None を返す。
    - rank, factor_summary: ランク生成（同順位の平均ランク処理）と基本統計量（count/mean/std/min/max/median）を提供。
  - zscore_normalize は kabusys.data.stats から再エクスポート（research パッケージ初期公開）。

- 運用上の堅牢性・設計上の注意点（全体）
  - ルックアヘッドバイアス回避: モジュール内で datetime.today() / date.today() の直接参照を避け、関数引数で日付を明示的に受け取る設計（テスト／検証に有利）。
  - DB 書き込みは冪等性を重視（BEGIN / DELETE / INSERT / COMMIT のパターン、ROLLBACK の試行とログ記録）。
  - OpenAI 呼び出しは JSON Mode を利用し、厳密な JSON 出力を期待するが、実際の出力の揺らぎに対して復元ロジックを実装（部分的な前後テキストを切り出して JSON を抽出する等）。
  - DuckDB の互換性（executemany の空リスト取り扱い等）に配慮した実装。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI API キー等の取り扱いは Settings 経由で環境変数から取得。自動ロードを無効化する仕組み（KABUSYS_DISABLE_AUTO_ENV_LOAD）を提供。

Notes / Known limitations
- 現時点で外部依存:
  - OpenAI SDK（OpenAI クライアント）を想定（gpt-4o-mini を利用）。
  - DuckDB をデータ格納／クエリ基盤として利用。
  - J-Quants クライアントモジュール（kabusys.data.jquants_client）に依存する処理（calendar_update_job 等）。
- 一部サブパッケージ（strategy, execution, monitoring）はパブリック API としてエクスポートされるものの、実装の詳細や追加機能は今後のリリースで拡充予定。

もし CHANGELOG に追加してほしい具体的な変更点（例: 実装されているが記載されていないモジュール、リリース日や取り消し・既知のバグ等）があれば教えてください。必要に応じて追記・修正します。