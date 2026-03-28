# Changelog

すべての著名な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

現在のバージョン: 0.1.0

未リリース
---------

（なし）

[0.1.0] - 2026-03-28
-------------------

初回公開リリース。主要な機能群を実装しました。設計上の注意点やフォールバック処理（フェイルセーフ）を多く取り入れ、テスト可能性と運用性を重視しています。

Added
- パッケージ基盤
  - kabusys パッケージ初期化（src/kabusys/__init__.py）。バージョン情報と主要サブパッケージの公開（data, strategy, execution, monitoring）を定義。
- 設定・環境変数管理（src/kabusys/config.py）
  - .env / .env.local 自動読み込み機能を実装。プロジェクトルートの探索は __file__ を起点に .git または pyproject.toml を検索して行うため、CWDに依存しない動作。
  - export KEY=val 形式やクォート・エスケープ、行末コメントの扱いに対応したパーサを実装。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 環境変数保護（OS環境変数を protected として .env.local の上書きから除外）を実装。
  - Settings クラスを提供し、各種必須値（J-Quants / kabu / Slack 等）や DB パス、実行環境（development/paper_trading/live）、ログレベルの検証を行うプロパティを公開。
  - 必須変数未設定時は明確な ValueError を送出する挙動。
- AI（自然言語処理）関連（src/kabusys/ai/）
  - ニュースセンチメント（score_news）
    - raw_news / news_symbols を集約し、銘柄ごとに記事を結合して OpenAI（gpt-4o-mini）へバッチ送信。バッチサイズ・文字数制限を導入してトークン肥大化を抑制。
    - JSON Mode を利用した厳格なレスポンス検証（レスポンス復元ロジック含む）、スコアの ±1.0 クリップ、部分成功時は該当銘柄のみ置換（DELETE → INSERT）して既存データ保護。
    - リトライポリシー（429/ネットワーク断/タイムアウト/5xx は指数バックオフでリトライ）とエラー時のフェイルセーフ（問題銘柄はスキップ）を実装。
    - DuckDB 0.10 の executemany 空リスト制約を考慮した実装。
    - calc_news_window ユーティリティ（JST基準のニュース収集ウィンドウ計算）を提供。
  - 市場レジーム判定（score_regime）
    - ETF（1321）の 200 日移動平均乖離（重み 70%）とマクロセンチメント（LLM 評価、重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロ記事抽出はキーワードマッチ（多言語キーワード含む）で行い、記事がない場合は LLM 呼び出しをスキップして macro_sentiment=0.0 を使用。
    - OpenAI 呼び出しは独立関数化し、unittest.mock.patch によりテスト差し替えが容易。
    - API エラー時のリトライ、500 系と非 5xx の扱い分離、レスポンスパース失敗時のフォールバックを実装。
- リサーチ（因子・特徴量探索）（src/kabusys/research/）
  - factor_research モジュール
    - モメンタム（1M/3M/6M リターン、MA200乖離）、ボラティリティ（20日 ATR、相対 ATR）、流動性指標（20日平均売買代金・出来高比）およびバリュー指標（PER、ROE）を DuckDB 上で計算する関数群（calc_momentum, calc_volatility, calc_value）を実装。
    - 大域定数（ホライズン日数、スキャンバッファ等）を明示。
    - データ不足時の None ハンドリング、結果は (date, code) をキーとした辞書リストで返却。
  - feature_exploration モジュール
    - 将来リターン計算（calc_forward_returns。可変ホライズン、入力検証あり）。
    - IC（Information Coefficient）計算（calc_ic。スピアマンランク相関、最小有効サンプルチェックあり）。
    - ランク変換ユーティリティ（rank。平均ランク、丸めで ties 対応）。
    - ファクター統計サマリー（factor_summary。count/mean/std/min/max/median を計算）。
  - research パッケージの公開 API を __init__ で整理。
- データプラットフォーム（src/kabusys/data/）
  - calendar_management モジュール
    - JPX カレンダー管理（market_calendar）を想定した営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB にカレンダーが存在しない場合は曜日ベースのフォールバック（平日=営業日）を採用し、一貫性を保つ設計。
    - calendar_update_job により J-Quants API から差分取得し冪等的に保存。バックフィル・先読み・健全性チェックを実装。
  - ETL パイプライン（pipeline.py / etl.py）
    - ETL 実行結果を表す ETLResult データクラスを実装（品質チェック結果・エラー一覧を含む）。
    - 差分取得、バックフィル、品質チェック（quality モジュールとの連携想定）を行うための基盤を実装。
    - jquants_client を利用した保存処理の前提で設計（idempotent 保存、ON CONFLICT ロジック想定）。
  - data パッケージの公開整備（etl を再エクスポートなど）。
- ドキュメント的コメント
  - 各モジュールに設計方針、処理フロー、重要な注意点（例: ルックアヘッドバイアスを避けるため date.today()/datetime.today() を直接参照しない等）を明記。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY を利用する仕様。未設定時は明確なエラーを投げることで誤動作を防止。

Notes（運用・開発上の重要事項）
- DuckDB バインド互換性
  - DuckDB 0.10 の executemany が空リストを受け付けない挙動を回避するため、executemany 呼び出し前に params が空でないことを確認する実装を採用。
- OpenAI 呼び出しのテスト容易性
  - 内部で _call_openai_api を別関数に抽出しているため、unittest.mock.patch により API 呼び出しを簡単にモック可能。
- フェイルセーフ方針
  - LLM 呼び出し失敗時はスコアを 0（中立）にフォールバック、もしくは当該チャンクをスキップして他の銘柄へ影響を波及させない設計。
- ルックアヘッドバイアス対策
  - 全ての期間指定ロジックは target_date 未満／以前のみを参照するよう設計。内部で現在時刻を無条件参照しないことに注意。

今後の予定（短期）
- strategy / execution / monitoring の実装拡充（現時点ではパッケージ公開のみ）。
- jquants_client や quality モジュールの具体的実装とそれらとの統合テスト強化。
- API 呼び出しのメトリクス収集・監視機構追加。

---

参照:
- パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)
- 実装ファイル: src/kabusys/{config.py, ai/, research/, data/}