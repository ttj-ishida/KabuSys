# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはコードベース（src/ 以下）の内容から実装された機能・設計方針・注意点を推測して作成した初期の変更履歴です。

## [Unreleased]
- 現時点で未リリースの変更はありません。

## [0.1.0] - 2026-04-04
初回リリース。以下の主要機能と設計方針を含みます。

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開インターフェースを追加（__version__ = 0.1.0）。
  - パッケージ公開モジュール: data, strategy, execution, monitoring を __all__ で明示。

- 環境設定 / コンフィグ
  - 環境変数・設定管理モジュール（kabusys.config）を追加。
    - プロジェクトルート自動検出（.git または pyproject.toml を起点）による .env / .env.local 自動読み込み機能。
    - .env パーサ実装（export 対応、クォート・エスケープ、インラインコメント処理）。
    - 自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）をサポート。
    - 環境変数の必須チェック用 _require() と Settings クラスを提供。J-Quants、kabu API、LINE、DBパス、監視用しきい値、実行環境判定など多数のプロパティを実装。
    - KABUSYS_ENV / LOG_LEVEL の検証ロジックを実装。

- AI（自然言語処理）機能
  - ニュースNLP スコアリングモジュール（kabusys.ai.news_nlp）
    - raw_news + news_symbols から銘柄ごとに記事を集約して OpenAI（gpt-4o-mini）へバッチ送信し、ai_scores テーブルへスコアを保存。
    - タイムウィンドウ計算（JST 基準 → UTC 変換）を提供（calc_news_window）。
    - バッチサイズ、記事件数・文字数上限、リトライ（429/ネットワーク/5xx に対する指数バックオフ）やレスポンスバリデーション実装。
    - レスポンスの JSON モードにおけるパース耐性（前後余計なテキスト対応、未知コードの無視、数値検証、±1.0 クリップ）。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能に設計（_call_openai_api を patch 可能）。
    - フェイルセーフ: API 失敗時は該当チャンクをスキップ、全体処理継続。

  - 市場レジーム判定モジュール（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - raw_news からマクロキーワードで記事タイトルを抽出し、OpenAI に JSON レスポンスを要求してセンチメントを取得。
    - API リトライ、5xx 判定、JSON パース例外時のフォールバック（macro_sentiment = 0.0）を実装。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実施。
    - ルックアヘッドバイアス回避のため datetime.today() を参照しない設計、prices_daily クエリに date < target_date の排他条件を使用。

- リサーチ / ファクター計算
  - kabusys.research パッケージと機能群を追加。
    - factor_research モジュール
      - モメンタム（1M/3M/6M リターン、ma200 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）およびバリュー（PER, ROE）計算を実装。
      - DuckDB SQL を用いたスキャン範囲バッファやデータ不足時の None 戻しを明示。
    - feature_exploration モジュール
      - 将来リターン計算（任意ホライズン）、スピアマンの IC（rank ベース）、ランク付けユーティリティ、統計サマリーを実装。
      - pandas 等の外部依存を避け、標準ライブラリと DuckDB のみで実装。
    - zscore_normalize 等のユーティリティは data.stats から提供される前提で再エクスポート。

- データプラットフォーム（Data）
  - calendar_management モジュール
    - JPX マーケットカレンダー管理、営業日判定、next/prev_trading_day、get_trading_days、is_sq_day を提供。
    - market_calendar が未取得の際は曜日（週末）ベースのフォールバックを使用する一貫した挙動。
    - 夜間バッチ更新ジョブ（calendar_update_job）を実装（J-Quants API 経由の差分取得、バックフィル、健全性チェック）。
  - ETL パイプライン（pipeline モジュール）
    - ETLResult データクラスを定義（取得・保存件数、品質問題、エラー一覧、ヘルパーメソッド）。
    - 差分更新、backfill、品質チェック連携、J-Quants クライアント（jquants_client）経由の idempotent 保存を設計方針として明記。
  - etl モジュールは pipeline.ETLResult の再エクスポートを提供。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーや各種シークレットは環境変数経由で管理する設計。必須キー未設定時は明示的に ValueError を送出して早期に検出。

### Notable implementation / 設計メモ
- ルックアヘッドバイアス対策として、すべての「日付を基準とした処理」は内部で datetime.today() / date.today() を参照せず、呼び出し側から target_date を受け取る設計になっています。
- DuckDB を主要なローカル DB として利用。executemany の空リストバインドに関する互換性考慮が行われています（DuckDB 0.10 の制約対策）。
- OpenAI 呼び出しは gpt-4o-mini + JSON mode を想定。レスポンスパースや不正応答への耐性（前後余計な文字抽出、未定義コードの無視、数値検証等）を強化。
- テスト容易性のために外部API呼び出しポイント（_call_openai_api 等）を patch 可能にしている点を意図的に設計。
- DB 書き込みは基本的に冪等（DELETE→INSERT など）を行い、部分失敗時でも既存データを不必要に消さない工夫をしている。

### Known issues / Limitations
- PBR や配当利回り等の一部バリューファクターは未実装（calc_value に注釈あり）。
- news_nlp のスコアは現フェーズで sentiment_score と ai_score を同じ値として扱う設計。
- OpenAI 依存の挙動（レイテンシ・コスト・API の仕様変更）に注意が必要。API レートや課金に関する運用設計は別途必要。

---

今後のリリースでは、以下のような項目が想定されます（例）:
- strategy / execution / monitoring モジュールの詳細実装と統合テスト追加
- 追加ファクターやバックテスト基盤の導入
- J-Quants / kabu API クライアントの安定化とモック対応の強化
- CI による自動テスト・静的解析・型チェックの導入

（この CHANGELOG はコードの現状から推測して作成しています。実際の変更履歴やコミットログがある場合はそれに基づいて更新してください。）