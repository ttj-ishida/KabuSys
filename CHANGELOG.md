# CHANGELOG

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-03-28

初回リリース。

### Added
- パッケージ基盤
  - パッケージ情報 (kabusys.__version__ = 0.1.0) と公開サブパッケージ一覧を追加。
- 環境設定 / 設定管理 (kabusys.config)
  - .env ファイルまたは OS 環境変数から設定を自動読み込みするユーティリティを実装。
  - プロジェクトルート検出: .git または pyproject.toml を起点に自動検出し、CWD に依存しない読み込みを実現。
  - .env のパーサは以下をサポート:
    - 空行 / コメント行、export KEY=val 形式
    - シングル／ダブルクォート内のバックスラッシュエスケープ
    - クォート無しの場合のインラインコメント削除（直前がスペース／タブの場合のみ）
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - Settings クラスを提供（J-Quants / kabuステーション / Slack / DB パス / env / log_level 等）。KABUSYS_ENV と LOG_LEVEL の値検証を実装。
- AI ニュース NLP (kabusys.ai.news_nlp)
  - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込み。
  - 時間ウィンドウは JST 基準で「前日15:00 ～ 当日08:30」を採用（内部は UTC naive datetime で処理）。
  - バッチ処理: 最大 20 銘柄ずつ送信し、1銘柄あたりの記事数・文字数上限を設定してトークン肥大化に対処。
  - JSON Mode + レスポンス検証を厳格に実施（results 配列・code/score 検証、未知コード無視、スコアを ±1 にクリップ）。
  - 再試行戦略: 429/ネットワーク断/タイムアウト/5xx を指数バックオフで再試行。失敗時は該当チャンクをスキップして継続。
  - テスト容易性: OpenAI 呼び出しをラップした内部関数を patch 可能（unittest.mock.patch による差し替え想定）。
  - DuckDB 0.10 の executemany 要件に配慮し、空パラメータを避ける実装。
- 市場レジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を組み合わせ、日次で市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ冪等で書き込み。
  - ETF の MA 計算は target_date 未満のデータのみを使用し、ルックアヘッドバイアスを排除。
  - マクロキーワードで raw_news をフィルタし、LLM（gpt-4o-mini）により JSON 出力で macro_sentiment を取得。
  - API 障害時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。OpenAI 呼び出しに対する再試行・5xx 判定・バックオフを実装。
  - 冪等性を保った DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を実施。書き込み失敗時は ROLLBACK を試行して例外を伝播。
- データ関連ユーティリティ (kabusys.data)
  - calendar_management:
    - JPX カレンダー管理／夜間更新ジョブ（calendar_update_job）を実装。J-Quants クライアント経由で差分取得し idempotent に保存。
    - 営業日判定関数群を提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - market_calendar 未取得時のフォールバックとして曜日日ベース（平日を営業日）判定を採用。最大探索範囲を設定して無限ループを防止。
    - バックフィル日数、先読み日数、健全性チェック（将来日付の異常検知）を実装。
  - pipeline / etl:
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。ETL のフェッチ／保存件数、品質問題、エラーを集約して返す。
    - 差分更新・バックフィル・品質チェック（quality モジュール経由）に関する基盤を実装。品質問題は収集して呼び出し元に委ねる設計。
- 研究用モジュール (kabusys.research)
  - ファクター計算:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を計算（データ不足時は None）。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: 最新財務データ（raw_financials）と株価から PER / ROE を算出。
  - 特徴量探索:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - calc_ic: スピアマン秩相関（ランクベース IC）を実装（少数レコード時は None を返す）。
    - rank: 同順位は平均ランクを返す安定的なランクセレクタ。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出。
  - zscore_normalize を kabusys.data.stats から再エクスポート。
- 設計方針・品質
  - 主要な日付処理関数群は datetime.today() / date.today() を直接参照せず、target_date を明示的に受け取ることでルックアヘッドバイアスを回避。
  - OpenAI など外部 API 呼び出しの失敗に対してフェイルセーフ（スコア 0 やスキップ）を採用し、ETL / バッチ処理全体を停止しないように設計。
  - DuckDB を組み合わせた SQL＋Python アプローチを採用。互換性のための実装上の注意（executemany の空リスト回避等）あり。

### Fixed
- 初回リリースのため特定の「修正」はなし（実装段階での堅牢性向上・エラー処理は上記 Added に含む）。

### Notes
- OpenAI には gpt-4o-mini を利用する想定で実装している（モデル名は定数で管理）。API キーは引数で注入可能（テスト容易性）かつ環境変数 OPENAI_API_KEY を参照。
- .env パーサおよび自動ロードは、開発／テスト時に予期せぬ環境上書きを防ぐため protected（OS 環境変数）概念を導入。
- DB 書き込みはできる限り冪等に実装（DELETE→INSERT 等）して再実行に耐える設計。
- Future: 本バージョンでは PBR・配当利回り等は未実装（calc_value の注釈参照）。

今後のリリースでは、追加指標・バックテスト・実取引連携（execution / monitoring）や性能改善、より詳細な品質チェックなどを予定しています。