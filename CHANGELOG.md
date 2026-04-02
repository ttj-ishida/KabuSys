# Changelog

すべての重要な変更点をここに記録します。フォーマットは "Keep a Changelog" に準拠します。

注: リリース日はソースコードからの推測に基づいています。

## [Unreleased]

## [0.1.0] - 2026-04-02
初回リリース。日本株自動売買・データ基盤・リサーチ向けの基盤モジュール群を追加しました。主な追加点は以下の通りです。

### 追加
- パッケージ基盤
  - パッケージ名: kabusys、バージョン: 0.1.0
  - パッケージの公開インターフェースに data / strategy / execution / monitoring を想定した __all__ を定義。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - 自動読み込みの優先順位: OS 環境変数 > .env.local > .env
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
    - プロジェクトルートは .git または pyproject.toml から探索して決定（CWD に依存しない）。
  - .env パーサーの実装:
    - コメント行・空行無視、export KEY=val 形式サポート、シングル/ダブルクォート内のバックスラッシュエスケープ対応、行内コメントの取り扱い等。
    - 既存 OS 環境変数を保護する protected オプション。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得可能:
    - J-Quants API / kabu ステーション API / Slack / DB パス (DuckDB / SQLite) / 監視閾値 / ログレベル / 実行環境フラグなど。
    - env 値や log_level の検証を実施（許可値以外は ValueError 発生）。
    - Path を返すプロパティは expanduser を適用。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を集約し、銘柄ごとにニュースをまとめて OpenAI (gpt-4o-mini) に送信してセンチメントを算出。
    - バッチ処理（最大 20 銘柄 / チャンク）、1 銘柄あたりの記事数上限・文字数トリムを実装。
    - OpenAI 呼び出しは JSON mode（厳密な JSON 出力を期待）で行い、レスポンスのバリデーションを実施。
    - 再試行ロジック（429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ）を備え、API 失敗時は該当チャンクをスキップして処理継続（フェイルセーフ）。
    - スコアは ±1.0 にクリップ、DuckDB への書き込みは部分失敗に備えて該当コードのみ DELETE→INSERT で置換（冪等性・既存データ保護）。
    - 時刻ウィンドウ計算 (前日 15:00 JST 〜 当日 08:30 JST を UTC に変換) を提供する calc_news_window。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジームを判定（bull/neutral/bear）。
    - prices_daily, raw_news, market_regime を参照して計算・DB へ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - OpenAI 呼び出しはニュース NLP とは独立した private 実装とし、API 失敗時は macro_sentiment=0.0 のフォールバック。
    - 設計上、datetime.today()/date.today() を直接参照せずルックアヘッドバイアスを防止。
    - リトライ・エラーハンドリングを実装（RateLimitError / APIConnectionError / APITimeoutError / APIError の扱いに差異あり）。

- データ関連モジュール (kabusys.data)
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを基に営業日判定・次/前営業日の計算・期間内営業日取得・SQ 判定等のユーティリティを提供。
    - market_calendar がない場合は曜日ベースのフォールバック（平日を営業日扱い）。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等に更新、バックフィル・健全性チェックを実装。
    - 探索上限日数を設定して無限ループを防止。
  - ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETL 実行結果を格納する ETLResult dataclass を実装（取得数・保存数・品質問題・エラー概要などを保持）。
    - 差分更新・保存（jquants_client 経由での冪等保存）・品質チェックの設計方針をコード化。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得など。
    - デフォルトのバックフィル日数やカレンダー先読み日数等の定数を定義。
  - jquants_client（参照のみ、実装は別モジュール想定）に依存。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research
    - Momentum (1M/3M/6M リターン)、200 日移動平均乖離、ATR（20 日）、20 日平均出来高・売買代金等を DuckDB 上で SQL と Python の組合せで計算。
    - 欠損データやデータ不足時の扱いを明確化（不足時は None）。
    - 結果は (date, code) をキーとする dict のリストで返却。
  - feature_exploration
    - 将来リターン計算 (calc_forward_returns)：指定ホライズン（営業日）分のリターンを同一クエリで取得。ホライズンのバリデーションあり。
    - IC（Information Coefficient）計算 (calc_ic)：ファクターと将来リターンのスピアマン順位相関を実装。データ不足（有効ペア < 3）で None を返す。
    - ランク変換ユーティリティ (rank)：同順位は平均ランクを返す実装、丸め処理で ties 判定の安定化。
    - 統計サマリー (factor_summary)：count/mean/std/min/max/median を計算。
  - research パッケージは data.stats.zscore_normalize を再利用可能にエクスポート。

### 設計方針・品質上の注意点（主要）
- ルックアヘッドバイアス防止:
  - 多くの処理で datetime.today()/date.today() を直接参照せず、呼び出し側から target_date を明示的に渡す設計。
  - DB クエリにおいて target_date 未満 / 以前 の排他条件を徹底。
- DB 書き込みの冪等性:
  - market_regime / ai_scores etc. で既存レコードを削除してから挿入するパターンを採用し、部分失敗時のデータ保護に留意。
- 外部 API 呼び出しに対する堅牢性:
  - OpenAI 呼び出しでのリトライ・バックオフ、非致命的フォールバック（macro_sentiment=0.0）を実装。
  - JSON レスポンスのバリデーションとフォールバック（レスポンス文字列から {} を抽出する等）。
- 依存:
  - DuckDB を主要なデータストア前提。
  - OpenAI Python SDK（OpenAI クライアント）を使用。
  - jquants_client を通じた外部 API との連携を想定。

### 既知の制約 / 未実装
- strategy / execution / monitoring パッケージは __all__ に含まれるが、本差分内に具体的な実装ファイルは含まれていません（将来的な追加想定）。
- 一部ファイル（pipeline の最後）が断片的に終わっている可能性があるため、ETL の最大日付取得ユーティリティ等の最終実装を要確認。
- jquants_client の具体実装はこの差分に含まれていない（外部モジュールとして想定）。

### セキュリティ
- 環境変数管理で OS 環境変数を保護する仕組み（protected keys）を導入。
- OpenAI API キーは明示的に引数または OPENAI_API_KEY 環境変数で渡す必要がある。未設定時は ValueError を送出。

---

今後の改善案（例）
- strategy / execution / monitoring の具体実装を追加してエンドツーエンドな発注・監視機能を完成させる。
- 単体・統合テストの追加（OpenAI 呼び出しと DB 書き込みのモック化）。
- jquants_client の実体と API 呼び出しのエラーハンドリング強化。
- ロギング・メトリクスの統一（監査ログやモニタリング用メトリクスの出力整備）。

--- 

（注）この CHANGELOG は提示されたソースコードの内容から推測して作成しています。実際の変更履歴やリリースノートはプロジェクト管理の記録に基づいて調整してください。