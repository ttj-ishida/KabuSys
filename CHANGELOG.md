# Changelog

すべての注目すべき変更をここに記載します。  
このファイルは Keep a Changelog の形式に従います。  

履歴はセマンティックバージョニングに基づき記載しています。

## [Unreleased]

- （現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-28

初回リリース。日本株自動売買・リサーチ用のコアライブラリを提供します。主な追加点は以下のとおりです。

### Added
- パッケージ初期化
  - パッケージ名: kabusys、バージョン 0.1.0 を設定。
  - public API として data, strategy, execution, monitoring を __all__ に公開（strategy / execution / monitoring は将来的な実装を想定）。

- 環境変数 / 設定管理 (kabusys.config)
  - .env ファイル（.env / .env.local）および OS 環境変数から設定を読み込む自動ロード機能を実装。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサはクォート・エスケープ・コメント・export 形式に対応。
  - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パス / 実行環境（development/paper_trading/live）/ログレベル等のプロパティを取得可能。
  - 必須環境変数未設定時は適切に ValueError を送出。

- データ基盤ユーティリティ (kabusys.data)
  - calendar_management:
    - JPX カレンダー管理、営業日判定 API を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar テーブルがない場合は曜日ベースのフォールバックを利用。
    - calendar_update_job により J-Quants API から差分取得して冪等保存する処理を実装（バックフィル・健全性チェックあり）。
  - pipeline / etl:
    - ETL パイプライン用の ETLResult データクラスを実装（取得数・保存数・品質問題・エラー情報を保持）。
    - 差分取得、バックフィル、品質チェックの設計方針に対応するためのユーティリティを含む。
  - jquants_client への呼び出しを想定したインターフェース設計（実装は別モジュール）。

- ニュース NLP / AI 周り (kabusys.ai)
  - news_nlp.score_news:
    - raw_news と news_symbols を基に、指定ウィンドウ（前日15:00 JST ～ 当日08:30 JST）に該当する記事を銘柄別に集約。
    - OpenAI（モデル: gpt-4o-mini）へバッチ（最大 20 銘柄/チャンク）で送信し、JSON mode でセンチメントスコアを取得。
    - レスポンスバリデーション、スコアの ±1.0 クリップ、DuckDB への冪等的な DELETE→INSERT 書き込みを実装。
    - 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - テスト用に _call_openai_api をモック可能に設計。
  - regime_detector.score_regime:
    - ETF 1321 の 200日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次市場レジーム（bull / neutral / bear）を判定。
    - prices_daily / raw_news を参照し、計算結果を market_regime テーブルへ冪等的に書き込む。
    - LLM 呼び出しに失敗した場合は macro_sentiment=0.0 としてフェイルセーフ動作。
    - OpenAI 呼び出しは内部で OpenAI クライアントを生成（api_key 引数または環境変数 OPENAI_API_KEY を使用）。
    - テスト用に _call_openai_api を差し替え可能。

- リサーチ/ファクター関連 (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、
      バリュー（PER、ROE）等のファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB に対する SQL ベースの実装で、外部 API へのアクセスを行わない設計。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク付けユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等の外部依存を避け、標準ライブラリと DuckDB で処理。

- テスト・運用に配慮した設計
  - すべての時刻ベース処理で datetime.today()/date.today() を直接参照しない設計（ルックアヘッドバイアス防止）。
  - DuckDB のバージョン差異（executemany の空リスト制約など）に配慮した実装。
  - ロギング、警告・例外ハンドリング、トランザクション（BEGIN / COMMIT / ROLLBACK）による冪等性確保。

### Changed
- （初回リリースのため、アップグレード履歴はありません）

### Fixed
- （初回リリースのため、修正履歴はありません）

### Security
- OpenAI API キーは外部設定（引数または環境変数 OPENAI_API_KEY）で注入する設計。コード内に埋め込みはしていません。

### Known limitations / Notes
- OpenAI の呼び出しは外部ネットワーク依存。API キー未設定時は score_news / score_regime は ValueError を送出する。
- news_nlp / regime_detector は gpt-4o-mini の JSON mode を使用することを前提としているため、将来のモデル・SDK 変更時に調整が必要になる可能性がある。
- jquants_client モジュール（fetch/save 実装）は本リリースに含まれない想定のため、実運用では適切なクライアント実装が必要。
- strategy / execution / monitoring の公開は将来のコンポーネント実装を想定（0.1.0 ではコアデータ処理と研究用モジュールを優先）。

## 未來の予定
- strategy / execution モジュールの実装（注文・ポジション管理、paper/live 切替対応）。
- より詳細な品質チェックモジュール（kabusys.data.quality）の強化。
- CI テスト用のモックインフラ整備（DuckDB 固有挙動の CI 対応）。

---

作成者: kabusys (開発チーム)  
注: 本 CHANGELOG はコードベースから推測して作成したもので、実際のリリースノートはプロジェクトのリリース方針に従って調整してください。