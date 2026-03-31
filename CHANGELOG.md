# CHANGELOG

すべての変更は「Keep a Changelog」の形式に準拠しています。  
リリース日はコードベースの現状（本ファイル生成日）に基づいています。各項目はコード内から推測できる実装内容・設計意図を要約したものです。

※注意: 実装は外部依存（OpenAI クライアント、J-Quants クライアント、DuckDB 等）を前提としています。動作には環境変数や外部 API の設定が必要です。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-31
初回公開（推測）。日本株自動売買プラットフォームのコア機能群をまとめて実装。

### 追加
- 基本パッケージ構成
  - パッケージエントリポイント: kabusys.__init__（バージョン 0.1.0、公開サブパッケージ: data, strategy, execution, monitoring を宣言）
- 設定・環境変数管理（kabusys.config）
  - .env ファイル自動読み込み機能（プロジェクトルート検出 .git / pyproject.toml ベース）
  - .env / .env.local の読み込み順序とオーバーライド制御、OS 環境変数保護（protected set）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込みの無効化
  - .env 行パーサ（コメント、export プレフィックス、シングル/ダブルクオートとエスケープを正しく扱う）
  - 必須環境変数取得関数と Settings クラス（J-Quants, kabu API, Slack, DB パス, 監視閾値, 環境・ログレベル検証など）
- AI（自然言語処理）モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - 指定タイムウィンドウの raw_news を銘柄ごとに集約し、OpenAI（gpt-4o-mini、JSON Mode）でセンチメントを取得して ai_scores テーブルへ書き込み
    - ウィンドウ計算（calc_news_window）（JST → UTC の明示的変換、半開区間）
    - バッチ処理（最大 20 銘柄 / コール）、1 銘柄あたりの記事数・文字数トリム
    - API リトライ（429 / ネットワーク / タイムアウト / 5xx を指数バックオフでリトライ）、非再試行エラーはスキップ
    - レスポンスの厳格な検証（JSON の復元処理、results 配列の構造検証、未知コード除外、スコアの数値/有限値検査）、スコアを ±1.0 にクリップ
    - DuckDB 用の書き込みは部分置換戦略（対象コードのみ DELETE → INSERT）で部分失敗時の既存データ保護
    - DuckDB executemany の空パラメータ制約への対応
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225 連動）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定
    - ma200_ratio 計算（target_date 未満のデータのみ使用しルックアヘッドを回避）
    - マクロニュース抽出（キーワードでフィルタ、上限記事数）
    - OpenAI 呼び出しとリトライ（API エラー・5xx の扱い、全失敗時は macro_sentiment=0.0 のフェイルセーフ）
    - レジームスコア合成とクリップ、冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - 設計方針明記: ルックアヘッド回避、API 失敗時のフォールバック、モジュール結合を避ける設計（OpenAI 呼び出しは news_nlp と共有しない）
- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を利用した営業日判定ユーティリティ群: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - カレンダーが未取得の場合の曜日ベースフォールバック（週末は非営業日）
    - 最大探索日数制限（無限ループ防止）や健全性チェック（将来日付の異常検知）
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等保存（バックフィル／健全性チェック／例外ハンドリング）
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラス（取得件数、保存件数、品質問題リスト、エラーリスト、ヘルパープロパティ）
    - ETL の差分取得・保存・品質チェックの設計（差分更新、バックフィル、品質チェックを収集して継続処理）
    - DuckDB テーブルの存在確認や最大日付取得などのユーティリティ
  - etl モジュール公開インターフェース（kabusys.data.etl）で ETLResult を再エクスポート
  - J-Quants クライアント連携を前提とした実装（jq.fetch_* / jq.save_* を利用する設計）
- リサーチ（kabusys.research）
  - factor_research
    - モメンタム (calc_momentum): 1M/3M/6M リターン、200 日 MA 偏差（データ不足時は None）
    - ボラティリティ/流動性 (calc_volatility): 20 日 ATR（true range の NULL 伝播制御）、相対 ATR、20 日平均売買代金、出来高比率
    - バリュー (calc_value): raw_financials から最新財務を取得し PER / ROE を算出（EPS が 0/NULL の場合は None）
    - DuckDB SQL + ウィンドウ関数を活用した実装、出力は (date, code) ベースの dict リスト
  - feature_exploration
    - 将来リターン計算 (calc_forward_returns): 複数ホライズン（デフォルト [1,5,21]）、LEAD を使って効率的に取得
    - IC（Information Coefficient）計算 (calc_ic): スピアマン相関（ランク化、同順位の平均ランク処理）、有効レコードが 3 未満の場合は None
    - ランク変換ユーティリティ (rank) と統計サマリー (factor_summary)
  - research パッケージの公開 API を整理（主要関数を __all__ でエクスポート）
- ロギングと設計上の堅牢性
  - 多くの関数で詳細な logging（info/warning/debug）を出力するよう実装
  - API 呼び出しでのリトライ・バックオフ、JSON パース失敗でのフェイルセーフ、DB 書き込みでのトランザクション保護（ROLLBACK 対応）
  - ルックアヘッドバイアス対策（内部で date.today() / datetime.today() を参照しない設計ポリシーの明示）

### 変更
- （初回リリースのため履歴上の変更はなし）

### 修正
- （初回リリースのため履歴上の修正はなし）

### 注意事項 / 既知の制約
- OpenAI（gpt-4o-mini）利用箇所は API キー（OPENAI_API_KEY）を引数または環境変数で渡す必要がある。未設定時は ValueError を送出する設計。
- J-Quants 関連処理は jquants_client（jq）に依存。外部 API の認証トークンやレスポンス構造が前提。
- DuckDB のバージョンによる executemany の振る舞い（空リスト不可）を考慮した実装が盛り込まれている。
- JSON Mode（OpenAI のレスポンスを厳密 JSON で得る機能）を前提にしているが、前後の余計なテキスト混入を復元する耐性も実装している。
- 一部のモジュール間で関数を意図的に共有しない設計（モジュール結合を低く保つ）。テスト時は内部の _call_openai_api をモックする設計が想定されている。
- 一部依存モジュール（strategy, execution, monitoring）の実体はパッケージに含まれる想定だが、このリリースでの実装状況はコードベースの抜粋に依存する。

### セキュリティ
- API トークンやシークレットは環境変数経由で取得（Settings クラス）。.env ファイルはローカルで管理する前提。
- .env 読み込みでは既存の OS 環境変数を保護する仕組みを実装。

---

今後の改善候補（コードから推測）
- strategy / execution / monitoring モジュールの具体実装（取引ロジック、注文実行、プロセス監視）の追加・整備
- 単体テスト・統合テストの充実（OpenAI / J-Quants のモックを使った CI）
- エラーハンドリングの詳細通知（Slack 通知等の運用通知の統合）
- パフォーマンスの計測と最適化（大量銘柄時のバッチ戦略、並列化）
- ドキュメント（API 使用法、DB スキーマ、運用手順）の整備

以上。必要であれば、各モジュールごとのより詳細な変更点やリリースノート風の英語版も作成できます。