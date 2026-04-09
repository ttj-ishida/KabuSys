# CHANGELOG

すべての注目すべき変更をここに記録します。本ファイルは「Keep a Changelog」形式に準拠します。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-09
初回公開リリース。本バージョンで導入された主要機能と設計方針を記載します。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名を `kabusys` として初期モジュール構成を提供。
  - バージョン情報を `src/kabusys/__init__.py` にて `__version__ = "0.1.0"` として管理。
  - モジュールの公開 API を `__all__` で整理（data, strategy, execution, monitoring 等を想定）。

- 環境設定 / ロード (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順: OS 環境変数 > .env.local > .env。
    - プロジェクトルート自動検出: `.git` または `pyproject.toml` を基準に親ディレクトリを探索。
    - 環境変数自動ロードを環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - `.env` パーサーを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ処理を考慮）。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得可能に。
    - J-Quants / kabu ステーション / LINE Messaging / DB パス / Paper Trading 周りの設定プロパティを用意。
    - `PAPER_FILL_MODE` の妥当性チェック（instant/partial/never/reject）。
    - `KABUSYS_ENV`（development, paper_trading, live）と `LOG_LEVEL` のバリデーション。
    - 監視関連の閾値（CPU・メモリ・ディスク）や pid / kill flag パスなど。

- AI ニュース NLP (src/kabusys/ai/news_nlp.py, src/kabusys/ai/__init__.py)
  - ニュース記事を OpenAI（gpt-4o-mini、JSON Mode）でセンチメント解析し、銘柄単位のスコアを `ai_scores` テーブルへ書き込む機能を実装。
  - 主な特徴:
    - タイムウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（UTC 変換で安全に比較）。
    - 銘柄ごとに最新記事を集約（最大記事数・最大文字数でトリム）。
    - 最大 20 銘柄単位でバッチ送信（_BATCH_SIZE）。
    - レスポンスは JSON モードで検証（不正レスポンスやテキスト混入を許容する復元処理を含む）。
    - リトライ戦略: 429・ネットワーク断・タイムアウト・5xx を対象に指数バックオフ。
    - スコアは ±1.0 にクリップ。
    - 部分失敗耐性: 成功した銘柄のみを DELETE→INSERT により差し替え、他銘柄データを保護。
  - 公開 API: `score_news(conn, target_date, api_key=None)` を提供（OpenAI API キーを引数または環境変数 `OPENAI_API_KEY` から取得）。

- AI 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロセンチメント（重み30%）を合成し、日次で市場レジーム（bull / neutral / bear）を判定。
  - 主な特徴:
    - MA 計算は target_date 未満のデータのみ使用しルックアヘッドバイアスを排除。
    - マクロニュースはキーワードフィルタで抽出し、LLM（gpt-4o-mini）でセンチメントを評価。
    - LLM 呼び出しはフェールセーフ設計（API 失敗時は macro_sentiment=0.0）。
    - レジームスコアはクリップしてラベル化し、`market_regime` テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
  - 公開 API: `score_regime(conn, target_date, api_key=None)` を提供。

- データ処理 / ETL（src/kabusys/data/pipeline.py / etl.py）
  - ETL 実行結果を表す `ETLResult` dataclass を追加（取得件数・保存件数・品質問題・エラーを格納）。
  - ETL の設計方針（差分取得、バックフィル、品質チェックの扱い等）を実装に反映。
  - `data.etl` で `ETLResult` を再エクスポート。

- マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
  - JPX カレンダーを管理するモジュールを追加。
  - 提供機能:
    - 営業日判定: is_trading_day / next_trading_day / prev_trading_day / get_trading_days
    - SQ 日判定: is_sq_day
    - 夜間バッチ更新ジョブ: calendar_update_job（J-Quants から差分取得して market_calendar を更新）
  - 設計上の特徴:
    - DB 登録がない場合は曜日ベースでフォールバック（土日を非営業日とする）。
    - 最大探索日数制限で無限ループを回避。
    - バックフィル日数、先読み日数、健全性チェックを実装。

- リサーチ / ファクター計算（src/kabusys/research/...）
  - ファクター計算モジュールを追加（prices_daily / raw_financials に依存）。
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離 (ma200_dev)。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率など。
    - calc_value: PER, ROE を raw_financials と prices_daily から計算。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 将来リターンを複数ホライズンで一括取得（LEAD を利用）。
    - calc_ic: スピアマンランク相関（IC）を実装（欠測・同一値処理を考慮）。
    - rank: 同順位は平均ランクを返す堅牢なランク関数。
    - factor_summary: 各ファクターの count/mean/std/min/max/median を計算。
  - すべて DuckDB SQL と標準ライブラリで実装。外部 API へはアクセスしない旨を保証。

- 内部実装上の耐障害性／互換性対応
  - DuckDB の executemany に空リストを渡せない問題への回避（空チェックを挿入）。
  - OpenAI 呼び出し箇所はテスト時にモック可能（内部呼出し関数に分離）。
  - JSON パース失敗に対する復元処理（文字列中の最外側 {} を抽出）を実装。
  - API エラーのステータスコード有無に依存しない安全な判定ロジック。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API キーは引数で明示的に渡すか環境変数 `OPENAI_API_KEY` を使用する設計。キーの自動ログ出力やファイル保存を行わないよう注意。

### 注意事項 / 設計上の決定
- ルックアヘッドバイアス対策として、どのモジュールも内部で datetime.today() / date.today() を直接参照せず、明示的な target_date を受け取る設計を採用。
- DB 書き込みは可能な限り冪等化（DELETE→INSERT または ON CONFLICT 相当）しており、部分失敗時に既存データを不必要に消さない保護が適用されている。
- OpenAI API 呼び出しは再試行・バックオフ戦略を取り入れ、API 側の一時不良に対してフォールバックを行う（例: スコア 0.0 で継続）。
- DuckDB をメインのローカル分析ストアとして利用することを前提に実装。

---

今後のリリース予定（例）
- strategy / execution / monitoring の具体実装追加（発注ロジック・モニタリング・プロセス管理）
- 単体テスト・CI 設定・型チェック強化
- API クライアント（J-Quants / kabu）周りの抽象化と差し替え可能性向上

（この CHANGELOG はコード内の実装内容から推測して作成しています。実際の変更履歴はリポジトリのコミットログをご参照ください。）