# Changelog

すべての変更は「Keep a Changelog」形式に従い、セマンティックバージョニングを使用します。  
各リリースは主にコードベースから推測した機能追加・設計方針・振る舞いを記載しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-03
初回リリース。日本株自動売買システムのデータ処理／リサーチ／AI評価基盤のコア機能を実装。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化・公開 API を定義（__version__ = 0.1.0、__all__ に data/strategy/execution/monitoring を設定）。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数からの設定自動ロード機能を実装。
    - ロード順序: OS 環境 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - プロジェクトルート探索は __file__ を起点に .git または pyproject.toml を探索（配布後も動作するように CWD に依存しない）。
  - .env パーサーの実装
    - コメント、空行、export プレフィックス、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメントの扱いを考慮。
  - 環境変数取得用 Settings クラスを実装（J-Quants / kabuステーション / LINE / DB パス / 監視設定 / システム設定）。
    - 必須変数未設定時は明確な ValueError を発生。
    - env, log_level に対するバリデーションと is_live/is_paper/is_dev の判定ヘルパー。

- データ（Data）基盤
  - calendar_management
    - JPX マーケットカレンダー管理（market_calendar）と営業日判定ユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days の各関数を提供。
    - DB にカレンダーが無い場合は曜日ベースのフォールバック（週末を非営業日）を行い、一貫性のある挙動を保証。
    - 夜間バッチ更新ジョブ calendar_update_job を実装（J-Quants から差分取得 → 保存）。バックフィル・健全性チェックあり。
  - ETL パイプライン（pipeline, etl）
    - ETLResult データクラスを公開（ETL 実行結果、品質チェック情報、エラー一覧を保持）。
    - ETL の設計方針、差分取得・バックフィル・品質チェックの取り扱いを実装方針として明記。
    - pipeline モジュールの ETLResult を使えるように etl で再エクスポート。

- AI (kabusys.ai)
  - news_nlp
    - raw_news テーブルを対象に OpenAI（gpt-4o-mini）でニュースセンチメントを銘柄ごとに評価して ai_scores テーブルへ書き込む処理を実装。
    - 処理の特徴：
      - タイムウィンドウ（前日15:00 JST〜当日08:30 JST）を calc_news_window で計算。
      - 銘柄ごとに記事を集約し、1銘柄あたり最大記事数・最大文字数でトリム。
      - 最大バッチサイズ 20 銘柄で API に送信。
      - JSON Mode のレスポンスを検証し、スコアを ±1.0 にクリップ。
      - 429 / 接続断 / タイムアウト / 5xx は指数バックオフでリトライ。部分失敗があっても他銘柄の既存スコアを消さないように DELETE→INSERT で置換。
      - API キーが無い場合は ValueError を投げる（呼び出し側で明示的に設定することを要求）。
  - regime_detector
    - ETF 1321（日本株・日経225連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ保存する処理を実装。
    - 処理の特徴：
      - prices_daily から ma200_ratio を計算（target_date 未満のデータのみを使用してルックアヘッドバイアスを防止）。
      - raw_news からマクロキーワードで抽出したタイトルを LLM に渡して macro_sentiment を算出。
      - レジームスコア合成後、閾値によりラベル決定し、冪等的に DB に書き込み（BEGIN/DELETE/INSERT/COMMIT）。API 失敗時は macro_sentiment=0.0 とするフェイルセーフ。
      - OpenAI API 呼び出しのリトライとエラー処理（RateLimit/接続/タイムアウト/5xx の扱い）を実装。

- リサーチ（kabusys.research）
  - factor_research
    - ファクター計算関数を実装（prices_daily / raw_financials 参照）:
      - calc_momentum：1M/3M/6M リターン、ma200 乖離率（データ不足時は None）。
      - calc_volatility：20日 ATR・相対 ATR、20日平均売買代金、出来高比率。
      - calc_value：PER（EPS が 0/欠損なら None）・ROE（最新財務データを target_date 以前から取得）。
    - SQL による効率的な集約実装と、営業日カバーのためのスキャンバッファを実装。
  - feature_exploration
    - calc_forward_returns：指定ホライズン（デフォルト [1,5,21]）での将来リターンを一度のクエリで取得する実装。horizons のバリデーションあり。
    - calc_ic：factor と将来リターンの Spearman ランク相関（IC）を計算する実装（有効レコード数が少ない場合は None を返す）。
    - rank：同順位は平均ランクで扱うランク関数を実装（丸めによる ties 対応）。
    - factor_summary：count/mean/std/min/max/median を算出する統計サマリー実装。
  - research パッケージの __all__ で主要関数を再エクスポート。

### Design / Safety / Compatibility notes
- ルックアヘッドバイアス対策：すべてのスコア計算・AI 呼び出しで内部的に datetime.today()/date.today() を直接参照しない実装方針を採用（caller が target_date を与える）。
- OpenAI 呼び出しは JSON Mode を利用し、レスポンスの頑健な検証とパース処理を実装（余分な前後テキストを修復する処理も含む）。
- API 呼び出しは 429・ネットワーク断・タイムアウト・5xx をリトライ対象とし、非 5xx の APIError は即座にフォールバック（再試行しない）する方針。
- DB 書き込みは基本的に冪等性を重視（DELETE→INSERT や ON CONFLICT 相当の扱い）し、部分失敗時に他コードの既存データを保護する実装を行っている。
- DuckDB のバージョン差異（executemany の空リスト扱い, リスト型バインドの挙動など）に配慮した互換実装が行われている。
- 環境変数ロードでは OS 側の既存変数を保護するため protected set を使った上書き制御を行う。

### Fixed
- 初回リリースのため該当なし。

### Changed
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

## 今後の想定（ヒント）
- strategy / execution / monitoring モジュールの実装（現在は __all__ に名前はあるがコード未提示）。
- jquants_client 実装の詳細（calendar / save_* / fetch_* 等）の追加および外部 API クライアントの抽象化。
- テスト用フックやモック可能性の拡充（例: OpenAI 呼び出しの差し替えは既に一部考慮済み）。

--- 
この CHANGELOG はコードベース（コメント・関数名・ドキュメントストリング）から推測して作成しています。実際の変更履歴やリリースノートはリポジトリのコミット履歴やリリース時のアーティファクトに基づき更新してください。