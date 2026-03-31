# Changelog

すべての注目すべき変更をここに記録します。  
このファイルは Keep a Changelog の慣例に従います。  

最新: 0.1.0

---

## [0.1.0] - 2026-03-31

初回リリース。日本株自動売買・リサーチ向けのコアライブラリを実装しました。主要な機能、公開 API、設計上の決定やフェイルセーフ動作について以下にまとめます。

### 追加 (Added)
- コアパッケージ構成
  - パッケージエントリポイント `kabusys` を実装し、バージョンを "0.1.0" に設定。
  - パブリックモジュール: data, strategy, execution, monitoring（__all__ に公開）。

- 設定・環境変数管理 (`kabusys.config`)
  - .env / .env.local 自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 自動ロード無効化オプション: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env パーサーは `export KEY=...`、シングル/ダブルクォート、バックスラッシュエスケープ、コメント処理（クォート有無でのコメント挙動差分）に対応。
  - 環境変数未設定時に例外を出す `_require` と、`Settings` クラスによる型付けされた設定プロパティを提供。
  - 設定例:
    - J-Quants / kabuAPI / Slack トークン関連必須プロパティ
    - DB パス (`DUCKDB_PATH`, `SQLITE_PATH`)、監視閾値 (`CPU_THRESHOLD_PCT` 等)
    - 環境 (`KABUSYS_ENV`: development/paper_trading/live) と `LOG_LEVEL` の検証
    - ライフゲーム判定補助プロパティ (`is_live`, `is_paper`, `is_dev`)

- AI モジュール (`kabusys.ai`)
  - ニュース NLP スコアリング (`news_nlp.score_news`)
    - raw_news と news_symbols を集約し、銘柄単位で OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコアを算出・ai_scores に書き込み。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC naive に変換）。
    - バッチサイズ、記事数・文字数トリム、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスバリデーション（JSON 抽出・検証・スコアの ±1 クリップ）等を実装。
    - フェイルセーフ: API 呼び出し失敗時は該当チャンクをスキップし、全体処理は継続。
    - DuckDB への書込みは冪等操作（対象コードのみ DELETE → INSERT）で実装。DuckDB の executemany 空リスト制約に留意。

  - 市場レジーム判定 (`ai.regime_detector.score_regime`)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離 (重み 70%) と、マクロニュースの LLM センチメント (重み 30%) を合成して日次レジーム（bull/neutral/bear）を作成。
    - ma200_ratio の計算は target_date 未満のデータのみを使用（ルックアヘッド排除）。
    - マクロ記事抽出は定義済みキーワードでフィルタ、LLM 呼び出しは最大リトライ、失敗時は macro_sentiment=0.0 にフォールバック。
    - 出力は `market_regime` テーブルへトランザクションで冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。

  - OpenAI 呼び出し点について
    - gpt-4o-mini、JSON mode 想定の実装。
    - テスト容易性のため `_call_openai_api` を内部で分離（ユニットテストでモック可能）。

- データプラットフォーム (`kabusys.data`)
  - カレンダー管理 (`data.calendar_management`)
    - JPX カレンダーの夜間バッチ更新ジョブ (`calendar_update_job`) を実装。J-Quants クライアントを介して差分取得→保存。
    - 営業日判定 API: `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day` を実装。DB 登録値優先、未登録日は曜日ベースでフォールバック。
    - 最大探索日数、バックフィル・健全性チェック等の安全装置を実装。

  - ETL パイプライン (`data.pipeline`, `data.etl`)
    - ETLResult dataclass を公開。ETL の取得数／保存数、品質問題、エラー概要を収集。
    - 差分取得、バックフィル、品質チェック（quality モジュールにより欠損・スパイク等検出）を想定する設計思想を実装。
    - jquants_client を用いた保存処理（idempotent 保存想定）との連携を想定。

- リサーチ機能 (`kabusys.research`)
  - ファクター計算 (`research.factor_research`)
    - Momentum（1M/3M/6M、MA200 乖離）、Volatility（20日 ATR、相対 ATR、平均売買代金等）、Value（PER/ROE）を DuckDB 上で計算する関数を提供。
    - 欠損・データ不足時は None を返して安全に扱える実装。
  - 特徴量探索 (`research.feature_exploration`)
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21] 日）、IC（Spearman ランク相関）、ファクター統計サマリー、ランク関数（同順位は平均ランク）等を実装。
    - pandas 等の外部依存を避け、標準ライブラリ + DuckDB のみで実装。

- 公開インターフェース/エクスポート
  - `kabusys.data.ETLResult` を再エクスポートする `data.etl`。
  - `kabusys.ai.score_news`, `kabusys.ai.score_regime` など主要関数を __all__ で公開。
  - `kabusys.research` は主要リサーチ関数をトップレベルで再エクスポート。

### 仕様・設計上の注意点 (Notes)
- ルックアヘッドバイアス防止
  - AI スコアリング・レジーム判定・ファクター計算は内部で datetime.today()/date.today() を直接参照しない設計。全て caller が与える target_date に基づく。
  - DB クエリにおいても date < target_date（または date = target_date）等で将来データを参照しないよう配慮。

- フェイルセーフ動作
  - OpenAI 等外部 API 呼び出しでエラーが発生した場合は、基本的に処理を中断せずフェイルセーフ（中立スコア = 0.0 など）で継続する実装。
  - ただし DB 書き込み失敗時はトランザクションを用い例外を上位に伝播する設計。

- トランザクション/冪等性
  - 市場レジームや ai_scores 等の書き込みは、既存行を削除してから挿入する冪等操作を行う（BEGIN/DELETE/INSERT/COMMIT）。失敗時は ROLLBACK を試行。

- DuckDB に関する互換性注意
  - 一部実装（executemany の空引数など）は DuckDB のバージョン依存性を考慮して条件分岐（空リストを送らない）を行っている。

- .env パーサーの挙動
  - クォートあり値はバックスラッシュでのエスケープ処理を行い、クォート閉じ以降はコメント等を無視。
  - クォートなし値は '#' の直前がスペースまたはタブの場合のみコメント扱い。

### 変更 (Changed)
- 初版のため該当なし。

### 修正 (Fixed)
- 初版のため該当なし。

### 非推奨 (Deprecated)
- 初版のため該当なし。

### 削除 (Removed)
- 初版のため該当なし。

### セキュリティ (Security)
- 初版: 特に既知のセキュリティ修正はありません。ただし、OpenAI/API キーや各種トークンは Settings 経由で必須チェックを行います。運用時は環境変数管理（.env の取り扱い）に注意してください。

---

今後の予定（推定）
- strategy / execution / monitoring モジュールの詳細実装および e2e テスト追加
- テストカバレッジ拡充（外部 API のモック化を含む）
- ドキュメント（Usage examples、API リファレンス）整備
- パッケージ化・リリース手順の自動化

もし特定の変更点（例えばリリース日付、追加・削除した機能の優先度等）をより詳細に反映したい場合は、対象箇所を教えてください。コードから推測できる範囲で CHANGELOG を更新します。