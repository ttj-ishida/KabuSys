# CHANGELOG

このプロジェクトは Keep a Changelog の形式に従って変更履歴を管理します。  
すべての重要な変更はセマンティックバージョニングに従ってタグ付けされます。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-03
初回リリース

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - パッケージ公開 API: data, strategy, execution, monitoring（__all__ にて公開）。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルと環境変数の読み込み機能を実装。プロジェクトルートの自動検出（.git または pyproject.toml を探索）により、CWD に依存しない自動ロードを実現。
  - .env パーサを実装（export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱い等に対応）。
  - .env 読み込みの優先順位は OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - 環境変数保護（protected set）機能を実装し、override の際に OS 環境変数を上書きしない安全仕様。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / システム設定（KABUSYS_ENV, LOG_LEVEL）の取得とバリデーションを行う。
  - KABUSYS_ENV と LOG_LEVEL の許容値チェックを実装。is_live / is_paper / is_dev のユーティリティを追加。

- AI モジュール (kabusys.ai)
  - news_nlp モジュール
    - raw_news と news_symbols を用いて銘柄ごとのニュースを前日15:00 JST〜当日08:30 JST のウィンドウで集約。
    - OpenAI (gpt-4o-mini) の JSON mode を用いたバッチセンチメント評価。1 チャンク当たり最大 20 銘柄、1銘柄あたり最大 10 記事・3000 文字までトリム。
    - API 呼び出しのリトライ（429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ）とフォールバック（失敗時は該当チャンクをスキップ）。
    - レスポンスの厳密なバリデーション（JSON抽出、results 配列、code と score の型チェック、未知コード無視、数値の有限性チェック）。
    - スコアは ±1.0 にクリップし、ai_scores テーブルへ冪等的に（DELETE → INSERT）書き込み。部分失敗時に既存の他コードスコアを保護する実装。
    - テスト容易性のため _call_openai_api を差し替え可能に設計。

  - regime_detector モジュール
    - ETF 1321（日経225連動）の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し、日次で market_regime を判定（'bull'/'neutral'/'bear'）。
    - ma200_ratio の算出は target_date 未満のデータのみを利用し、ルックアヘッドバイアスを防止。
    - マクロ関連記事は定義済みキーワードでフィルタし、OpenAI で -1.0〜1.0 の JSON スコアを取得。API エラー時は macro_sentiment=0.0 でフェイルセーフ継続。
    - レジームスコア合成ロジック、閾値判定、そして市場レジーム結果を冪等的に DB へ書き込む（BEGIN / DELETE / INSERT / COMMIT）。
    - OpenAI クライアント呼び出しは独立実装でモジュール結合を避ける設計。

- データ処理 / ETL / カレンダー (kabusys.data)
  - calendar_management モジュール
    - market_calendar テーブルを用いた営業日判定ロジックを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータがない場合は曜日（平日）ベースのフォールバックを行い一貫性を確保。
    - calendar_update_job を実装し、J-Quants API から差分取得・バックフィル（直近 _BACKFILL_DAYS）して market_calendar を冪等保存。健全性チェックを備え異常な将来日付を検出してスキップ。
  - pipeline / etl モジュール
    - ETLResult データクラスを提供し、ETL 実行結果（取得数・保存数・品質問題・エラー）の集約と辞書化（to_dict）をサポート。
    - 差分更新・バックフィル・品質チェックの設計方針を実装に反映。J-Quants の idempotent 保存関数と組み合わせて安全な ETL を実現。
    - DuckDB の制約（executemany の空リスト不可など）に配慮した実装。

- 研究用ユーティリティ (kabusys.research)
  - factor_research モジュール
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（20日 ATR）、流動性指標（20日平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB 上の SQL で計算する関数群（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None 処理、スキャン範囲バッファやウィンドウ設計など実運用を考慮した実装。
  - feature_exploration モジュール
    - 将来リターン計算（calc_forward_returns: 任意ホライズン対応、入力検証あり）。
    - IC（Information Coefficient）計算（calc_ic: スピアマンランク相関）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）。
    - pandas 等に依存しない純標準ライブラリ + DuckDB 実装。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Notes / Implementation details
- ルックアヘッドバイアス回避: AI / 調査系の関数は datetime.today()/date.today() を直接参照せず、必ず target_date を受け取る設計。
- エラー耐性: OpenAI API 呼び出しでの一時エラーやパースエラーはフェイルセーフ（スコア 0.0 或いは該当チャンクスキップ）で継続する方針。DB 書き込み時はトランザクションを用いて ROLLBACK を試み、失敗した場合は上位へ例外を伝播。
- テスト性: _call_openai_api 等の内部関数は unittest.mock.patch による差し替えが容易な設計。
- DuckDB 互換性: executemany の空リスト制約や日付型の扱いに配慮した実装を行っている。

---

今後のリリースでは、strategy / execution / monitoring の実装詳細、追加の品質チェックルール、より多様なモデルサポートやメトリクス監視機能を予定しています。