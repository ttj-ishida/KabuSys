# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠し、セマンティック バージョニングを使用します。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-27

初回リリース。日本株自動売買プラットフォーム "KabuSys" のコアライブラリを公開しました。以下の主要機能・モジュールを含みます。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージの __version__ を "0.1.0" に設定。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ に定義。

- 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動読み込み機能を実装。
  - 自動ロードの探索はパッケクト内の __file__ を起点に .git または pyproject.toml を基準にプロジェクトルートを特定（CWD 非依存）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）。
  - .env パーサ実装:
    - 空行・コメント（#）対応、export KEY=val 形式に対応。
    - シングル/ダブルクォート対応（バックスラッシュエスケープを解釈）。
    - クォートなし値のインラインコメント判定（直前が空白/タブの場合のみ '#' をコメントと判定）。
  - _load_env_file で override と protected キーを扱い、OS 環境変数の上書き保護を実装。
  - Settings クラスを提供し、各種必須設定の取得メソッドを実装（取得失敗時に ValueError を送出）。
    - J-Quants / kabuAPI / Slack / DB パスなどの設定をプロパティで提供。
    - KABUSYS_ENV と LOG_LEVEL のバリデーション実装（許容値を限定）。
    - duckdb/sqlite のデフォルトパスを提供（data/kabusys.duckdb, data/monitoring.db）。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini, JSON Mode）に送信しセンチメントを取得。
    - バッチ処理（最大 20 銘柄 / チャンク）、1 銘柄あたりの記事数上限・文字数上限（トークン肥大対策）。
    - 再試行ロジック（429/ネットワーク断/タイムアウト/5xx を指数バックオフでリトライ）。
    - レスポンスの厳格なバリデーション（JSON 抽出、results 配列、code と score、未知コード除外、数値検査）。
    - スコアは ±1.0 にクリップ。部分失敗に備え、書き込みはスコア取得済みコードのみ DELETE → INSERT （トランザクション、ROLLBACK 対策）。
    - テスト容易性のため _call_openai_api をパッチ可能に実装。
    - datetime.today()/date.today() を直接参照せず、target_date ベースのウィンドウ計算でルックアヘッドバイアスを回避。
    - DuckDB executemany に関する互換性考慮（空リストを渡さない安全実装）。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を生成。
    - マクロニュースは news_nlp.calc_news_window で定義される時間窓から抽出し、OpenAI（gpt-4o-mini）でスコアリング。
    - LLM エラーやレスポンスパース失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - レジーム合成後、market_regime テーブルへ冪等的に保存（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK とログ）。

- データモジュール (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX マーケットカレンダーの扱い（market_calendar）と営業日判定ユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB 登録値優先、未登録日は曜日ベースでフォールバック（週末除外）。
    - 最大探索日数制限で無限ループを防止。
    - calendar_update_job を実装し、J-Quants API から差分取得 → 保存（バックフィル・健全性チェック含む）。
    - jquants_client 経由での取得・保存を想定（例外時はログ出力して 0 を返却）。

  - ETL パイプライン (kabusys.data.pipeline, etl 再エクスポート)
    - ETLResult データクラスを追加（ETL 実行結果の集約: fetched / saved / quality_issues / errors 等）。
    - 差分更新、バックフィル、品質チェックのフレームワーク方針をドキュメント化。
    - _get_max_date/_table_exists 等のユーティリティを提供。
    - ETLResult.to_dict で品質問題をシリアライズ可能に実装。
    - kabusys.data.etl で ETLResult を再エクスポート。

- リサーチモジュール (kabusys.research)
  - factor_research
    - モメンタム（1M/3M/6M、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER, ROE）を計算する関数を実装。
    - DuckDB 上の SQL ウィンドウ関数を使った効率的実装。
    - 不足データ時は None を返す設計、結果は (date, code) をキーとする dict のリストで返却。
  - feature_exploration
    - 将来リターン calc_forward_returns（任意ホライズン、入力バリデーション付き）。
    - IC 計算 calc_ic（スピアマン ρ、ランク同位は平均ランク）。
    - ランク変換 rank（同順位は平均ランク、丸めで ties 検出の安定化）。
    - factor_summary（count/mean/std/min/max/median）を実装。
    - 外部依存無し（標準ライブラリのみ）での統計処理。

### 改善 (Changed)
- モジュール設計/堅牢性
  - DuckDB を前提とした SQL 実装にて、実行時の互換性（executemany の空パラメータ回避など）を考慮。
  - API 呼び出し周り（OpenAI）のリトライ戦略やログ出力を統一して実装。
  - ルックアヘッドバイアス対策を徹底（日付処理はすべて target_date ベース）。

### 修正 (Fixed)
- 本リリースは初回公開のため後方互換性の修正はなし。

### その他（設計上の注記）
- OpenAI API の呼び出しは gpt-4o-mini / JSON Mode を使用する想定。API キーは関数引数または環境変数 OPENAI_API_KEY で渡す。未設定の場合は ValueError を送出して呼び出し側で対処する。
- DB 書き込みはトランザクションで保護し、部分失敗時は既存データを不必要に削除しない戦略を採用（例: ai_scores は取得済みコードのみ書き換え）。
- テスト容易性を重視し、OpenAI 呼び出しのラッパー関数（_call_openai_api）をモック差し替え可能にしている。
- 外部依存は最小限（duckdb, openai 等）に留め、内部ロジックは標準ライブラリで完結するよう設計。

---

今後のリリースでは、strategy / execution / monitoring 関連の実装、J-Quants / kabu ステーション向けの実トレード連携、より詳細な品質チェック・監視機構の追加を予定しています。