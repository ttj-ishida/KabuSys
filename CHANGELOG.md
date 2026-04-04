Keep a Changelog に従った CHANGELOG.md（日本語）を作成しました。コードベース（初期リリース相当）から推測できる追加機能・設計方針・注意点をまとめています。

CHANGELOG.md
=============
すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  

Unreleased
----------
- なし

0.1.0 - 2026-04-04
------------------
追加 (Added)
- パッケージ初期リリース相当の機能群を追加。
  - kabusys パッケージのエントリポイントを追加（__version__ = "0.1.0"）。
  - モジュール公開: data, strategy, execution, monitoring を __all__ に登録。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルート判別は .git または pyproject.toml を基準に探索（CWD 非依存）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途想定）。
  - .env の行パーサを実装（コメント行、export プレフィクス、シングル/ダブルクォート、エスケープ、インラインコメント処理対応）。
  - 環境変数取得ユーティリティ Settings を提供（J-Quants / kabu / LINE / DB / 監視 / システム関連プロパティ）。
    - 必須値未設定時は ValueError を送出する _require を実装。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値セットを明示）。
    - デフォルト値（例: KABUSYS_API_BASE_URL, DUCKDB_PATH, PID_FILE_PATH 等）を定義。

- AI（自然言語処理）機能 (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp)
    - raw_news と news_symbols を集約して銘柄ごとのニューステキストを作成。
    - OpenAI (gpt-4o-mini) を JSON Mode で呼び出し、銘柄ごとのセンチメント（-1.0〜1.0）を取得。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄/コール）、1銘柄あたりの最大記事数／文字数制限 (_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK) を実装。
    - 再試行ロジック: 429 / ネットワーク断 / タイムアウト / 5xx サーバーエラーを指数バックオフでリトライ。
    - レスポンスのバリデーションとパース耐性（前後余計テキストから最外の {} を抽出する復元処理等）。
    - スコアは ±1.0 にクリップ。
    - スコア取得済み銘柄のみを DELETE → INSERT により置換して部分失敗時に既存スコアを保護（DuckDB の executemany 空リスト対策を反映）。
    - テスト容易化のため _call_openai_api を patch 可能に設計。
    - calc_news_window 公開: タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST に対応、UTC naive datetime を返す）。

  - 市場レジーム判定 (regime_detector)
    - ETF 1321（日経225連動型）の 200日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - LLM 呼び出しは独立実装（news_nlp と private 関数を共有しない設計）で、失敗時は macro_sentiment = 0.0 にフォールバックする安全設計。
    - MA 計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを防止。
    - OpenAI 呼び出しは再試行・例外分類を含む堅牢な実装。
    - 結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT。失敗時は ROLLBACK を試行し例外を伝播）。

- データプラットフォーム (kabusys.data)
  - 市場カレンダー管理 (calendar_management)
    - market_calendar テーブルの有無に応じた営業日判定関数を提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB 登録値を優先し、未登録日は曜日ベースでフォールバックする一貫したロジックを採用。
    - next/prev_trading_day の最大探索日数制限を設け無限ループを回避（_MAX_SEARCH_DAYS）。
    - calendar_update_job を実装: J-Quants API から差分取得→保存（バックフィル・健全性チェックあり）。
    - jquants_client を介した fetch/save の呼び出しを想定。

  - ETL / パイプライン (pipeline, etl)
    - ETLResult データクラスを公開（target_date, fetched/saved counts, quality_issues, errors 等）。
    - 差分取得・バックフィル・品質チェック（quality モジュール統合）を前提とした設計方針を実装。
    - jquants_client を用いた idempotent 保存（ON CONFLICT DO UPDATE）を想定。
    - ETL の実行結果を辞書化する to_dict を提供（品質問題を簡潔な dict に変換）。

- 研究用ユーティリティ (kabusys.research)
  - ファクター計算 (factor_research)
    - Momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）。
    - Volatility / Liquidity: 20日 ATR（atr_20・atr_pct）、20日平均売買代金、出来高比率。
    - Value: PER（price / EPS、EPS=0/欠損時は None）、ROE（raw_financials から最新値）。
    - DuckDB SQL を主体とした実装で、prices_daily / raw_financials のみ参照する安全設計。
    - データ不足時の None ハンドリングやログ出力あり。

  - 特徴量探索 (feature_exploration)
    - 将来リターン計算 calc_forward_returns（複数ホライズン同時取得、horizons 検証）。
    - IC（Information Coefficient）計算 calc_ic（Spearman ρ 相当。3レコード未満は None を返す）。
    - ランキング関数 rank（同順位は平均ランク、丸め処理で ties の検出漏れを低減）。
    - 統計サマリー factor_summary（count/mean/std/min/max/median を計算、None 値除外）。
    - pandas など外部ライブラリに依存しない実装を意図。

変更 (Changed)
- 初期バージョンのため過去の変更履歴はなし。設計観点で以下を明記:
  - ルックアヘッドバイアス回避のため、全ての時間依存処理は datetime.today()/date.today() を参照せず、関数引数で target_date を受け取る設計。
  - OpenAI 呼び出し周りはテストで差し替え可能なフック（_call_openai_api）が用意されている。

修正 (Fixed)
- 初期リリースのためなし。

廃止 (Deprecated)
- なし。

セキュリティ (Security)
- 初期リリースのため既知のセキュリティ修正はなし。ただし以下に注意:
  - OpenAI API キー・J-Quants トークン等の秘密情報は環境変数で管理すること。Settings は必須変数未設定時に例外を投げるため、CI/本番での環境設定を確認してください。
  - .env 自動読み込みはデフォルトで有効。テストや環境制御が必要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

注意事項（実装から推測）
- 依存:
  - DuckDB を DB 層として利用する想定（DuckDB の executemany の挙動に対する互換性考慮がある）。
  - OpenAI の Python SDK（OpenAI クライアント）を利用する想定。モデル名は gpt-4o-mini を指定。
  - J-Quants クライアントモジュール（kabusys.data.jquants_client）が存在し、fetch/save 関数を通じて外部 API にアクセス。
- 必須環境変数（代表例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は Settings のプロパティで必須とされている（未設定時は ValueError）。
  - OPENAI_API_KEY は news_nlp / regime_detector の呼び出し時に必須（引数経由でも渡せる）。
- テストのしやすさ:
  - OpenAI 呼び出しを patch してモック化できる設計。
  - .env 自動読み込みを無効化できるためユニットテストで環境を固定化可能。

今後の候補（コードから読み取れる拡張余地）
- strategy / execution / monitoring モジュールの具体的な公開 API 実装（現在は __all__ に含めるのみ）。
- ai モジュールでのレスポンス解析ロギング強化やメトリクス計測。
- ETL のパイプライン化、スケジューリングや監視（現状はロジックを提供するレイヤー）。
- エラーレベルやログの構成をさらに明文化してドキュメント化。

---

この CHANGELOG は現行コードから推測可能な「機能追加」「設計方針」「注意点」を整理したものです。実際のコミット履歴やリリース方針に合わせて分類・文言を調整してください。必要であれば英語版や Git タグ付け用の短縮文も作成します。