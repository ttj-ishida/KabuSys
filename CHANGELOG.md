# Changelog

すべての重要な変更履歴をここに記載します。  
このファイルは Keep a Changelog の書式に準拠しています。

注: 下記の内容はコードベースの実装内容から推測して記載しています。実際のリリースノート作成時は必要に応じて調整してください。

## [Unreleased]

## [0.1.0] - 初版
最初の公開リリース相当。以下の主要コンポーネントと機能を実装しています。

### 追加 (Added)
- パッケージの基本構造を追加
  - パッケージ名: `kabusys`
  - バージョン定義: `__version__ = "0.1.0"`
  - パッケージ公開 API: `data`, `strategy`, `execution`, `monitoring`（エントリポイントとしてエクスポート）

- 設定・環境変数管理 (`kabusys.config`)
  - .env ファイル自動読み込み機構を実装（プロジェクトルート検出: `.git` または `pyproject.toml` を起点）
  - 読み込み優先順位: OS 環境変数 > `.env.local` > `.env`
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD` 環境変数で自動ロードを無効化可能
  - `.env` パーサを実装（`export KEY=val` 対応、クォート内エスケープ、コメント処理）
  - 既存 OS 環境変数を保護するための protected キー管理、`override` オプションを提供
  - `Settings` クラスを提供し、アプリケーション設定アクセスを集中化
    - J-Quants / kabuステーション / LINE API / DB パス / 監視閾値 / 環境種別・ログレベル検証などのプロパティを実装
    - 入力検証（`KABUSYS_ENV`, `LOG_LEVEL` の許容値チェック）と利便性メソッド (`is_live`, `is_paper`, `is_dev`) を追加
    - 必須環境変数が未設定時に明確なエラーメッセージを投げる `_require` 実装

- AI（自然言語処理）モジュール (`kabusys.ai`)
  - ニュース NLP スコアリング (`kabusys.ai.news_nlp`)
    - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント算出機能を実装（`score_news`）
    - タイムウィンドウ設計（JST ベース: 前日 15:00 〜 当日 08:30、内部は UTC naive datetime）
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約（記事数 / 文字数トリム）
    - バッチ処理（1 回の API 呼び出しで最大 20 銘柄）とリトライ（429/接続断/タイムアウト/5xx に対する指数バックオフ）
    - OpenAI の JSON Mode を前提としたレスポンス検証と堅牢なパース処理（余分な前後テキスト回復ロジック含む）
    - スコアの ±1.0 クリップ、部分成功時に既存スコアを保護するための差し替えロジック（DELETE → INSERT）
    - テスト容易性のため OpenAI 呼び出しを差し替え可能に設計（`_call_openai_api` を patch 可能）
    - ログ出力で処理状況を可視化（対象記事数・チャンク数・書込銘柄数など）

  - 市場レジーム判定 (`kabusys.ai.regime_detector`)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジームを判定（`score_regime`）
    - MA200 計算におけるルックアヘッド防止（target_date 未満のみ参照）
    - マクロキーワードで raw_news をフィルタして LLM でセンチメント算出（記事が無い場合は LLM 呼び出しをスキップ）
    - OpenAI 呼び出しに対するリトライ/エラーハンドリング（RateLimit/接続/タイムアウト/5xx の再試行）
    - 計算結果を `market_regime` テーブルへ冪等的に書き込むトランザクション処理（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）

- データプラットフォーム関連 (`kabusys.data`)
  - カレンダー管理 (`kabusys.data.calendar_management`)
    - `market_calendar` テーブルに基づく営業日判定・探索ユーティリティを実装
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB にデータが無い/未登録の場合の曜日ベースフォールバック（主に土日判定）
    - 最大探索範囲制限による無限ループ防止、健全性チェック、バックフィル戦略
    - 夜間バッチ更新ジョブ `calendar_update_job` を実装（J-Quants から差分取得して保存、バックフィル、異常検知）

  - ETL / パイプライン (`kabusys.data.pipeline`, `kabusys.data.etl`)
    - ETL 実行結果を表す `ETLResult` データクラスを追加（取得/保存数、品質問題、エラー一覧を保持）
    - 差分取得、バックフィル、品質チェック（`kabusys.data.quality` と連携）を想定した設計
    - jquants_client 経由でのデータ取得と idempotent な保存（ON CONFLICT 相当）を前提とする実装方針

- リサーチ / ファクター分析 (`kabusys.research`)
  - ファクター計算群を実装（`kabusys.research.factor_research`）
    - モメンタム: 1M/3M/6M リターン、200 日 MA 乖離（`calc_momentum`）
    - ボラティリティ / 流動性: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率（`calc_volatility`）
    - バリュー: PER, ROE（`calc_value`、`raw_financials` を参照して直近の財務情報を結合）
    - 全て DuckDB 上の SQL とウィンドウ関数を主体に実装（外部 API 呼び出し無し、ルックアヘッド回避）
  - 特徴量探索ユーティリティ（`kabusys.research.feature_exploration`）
    - 将来リターン計算（`calc_forward_returns`、複数ホライズン対応、入力検証あり）
    - IC（Information Coefficient）計算（Spearman ランク相関、`calc_ic`）
    - 値のランク変換ユーティリティ（同順位は平均ランク、`rank`）
    - ファクター統計サマリー（count/mean/std/min/max/median、`factor_summary`）
  - 研究向け API 群をトップレベルで再エクスポート（利便性向上）

### 修正 (Changed)
- なし（初回実装のため該当なし）

### 修正 (Fixed)
- なし（初回実装のため該当なし）

### 削除 (Removed)
- なし（初回実装のため該当なし）

### 設計上の重要ポイント・ノート
- すべてのデータ処理関数は可能な限り「ルックアヘッドバイアス」を避ける設計（datetime.today()/date.today() に依存しない、クエリで date < target_date などを厳格に適用）。
- OpenAI への呼び出しは明示的にエラーハンドリングと再試行を組み込み、API 失敗時はフェイルセーフ（デフォルトスコア 0.0）で継続する方針。
- DB 書き込みは冪等性を意識（DELETE→INSERT、ON CONFLICT 相当の運用）して部分失敗時に既存データを過度に消さないように設計。
- テスト容易性を考慮し、外部 API 呼び出し（OpenAI 等）を差し替え可能に実装（モジュール内プライベート関数を patch 可能）。
- DuckDB を主要なローカル分析 DB として想定し、SQL ウィンドウ関数を多用して高効率に集計・ウィンドウ計算を実行。

---

今後のリリース案（提案）
- Unreleased にてバグ修正、ドキュメント整備、ユニットテスト拡充、CI/CD とデプロイ手順の追加を検討してください。必要であれば CHANGELOG の各項目を日付付きで切り分け、セマンティックバージョニングに基づく詳細を追加できます。