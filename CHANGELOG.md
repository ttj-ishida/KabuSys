# CHANGELOG

すべての重要な変更点をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。
※この CHANGELOG はコードベースの内容から推測して作成しています。

## Unreleased

- 今後の変更をここに記載します。

---

## 0.1.0 - 2026-04-04

初期リリース（推測）。日本株自動売買・データ処理・リサーチ基盤の第一版として以下の主要機能と実装方針を提供します。

### Added
- パッケージ基礎
  - kabusys パッケージの公開（__version__ = 0.1.0）。
  - 公開モジュール: data, strategy, execution, monitoring。
- 設定管理
  - 環境変数・設定管理モジュール（kabusys.config）。
  - .env/.env.local 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を起点）。
  - .env パーサ実装（export プレフィックス対応、シングル/ダブルクォート・エスケープ処理、インラインコメントの扱い）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスで主要設定をプロパティ化（J-Quants トークン、kabu API 設定、LINE 設定、DB パス、監視閾値、環境・ログレベル判定等）。
  - 環境値のバリデーション（KABUSYS_ENV / LOG_LEVEL の許容値チェック）。
- AI（NLP）モジュール
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）にバッチ送信し、銘柄毎の ai_scores を生成・保存する機能。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC ベースで処理）。
    - バッチ処理（最大 20 銘柄 / チャンク）、各銘柄のトリミング（最大記事数／文字数制限）。
    - OpenAI 回線障害・429・5xx に対する指数バックオフ付きリトライ。
    - レスポンスの堅牢なバリデーション・JSON 抽出（前後ノイズへの耐性）、スコアのクリップ。
    - DuckDB への冪等置換（該当コードのみ DELETE → INSERT）を実装。
    - テスト用フック: _call_openai_api をモック可能。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - LLM は gpt-4o-mini を想定。API 障害時は macro_sentiment を 0.0 としてフォールバック。
    - DuckDB の prices_daily/raw_news/market_regime を利用し、レジーム結果を冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - レトライ・エラーハンドリング（RateLimit, APIConnectionError, APITimeout, APIError の扱い）を実装。
- データ基盤（Data）
  - ETL パイプライン API（kabusys.data.pipeline）
    - ETLResult dataclass を公開（ETL 実行結果、品質チェック問題、エラー情報を格納）。
    - 差分更新、バックフィル、品質チェックの設計方針を実装（抽象的に）。
  - ETL の公開インターフェース（kabusys.data.etl）で ETLResult を再エクスポート。
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を基にした営業日判定・前後営業日探索・期間内営業日リスト等のユーティリティを提供。
    - DB 登録値優先、未登録日は曜日（平日）フォールバックの一貫した挙動。
    - calendar_update_job: J-Quants から差分取得 → 冪等保存（バックフィル・健全性チェックあり）。
    - 最大探索日数 (_MAX_SEARCH_DAYS) で無限ループ回避。
- リサーチ機能（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Volatility（20日 ATR 等）、Value（PER, ROE）を DuckDB から計算して返す関数を提供。
    - データ不足時の None 扱い、営業日スキャンバッファ等の設計を採用。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（複数ホライズン）、IC（Spearman ランク相関）計算、ファクター統計サマリー、ランク化ユーティリティを提供。
    - pandas 等外部依存無しで実装。
- ロギングとデバッグ情報
  - 各所で詳細な logging（info/debug/warning/exception）を実装。重要なフォールバックやデータ不足時に警告を出力。

### Changed
- （初期リリースのためなし）

### Fixed
- （初期リリースのためなし）

### Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY で提供する必要があり、未設定時は ValueError を送出することで誤操作を防止。

### Design / Implementation Notes
- ルックアヘッドバイアス対策として、どのモジュールも datetime.today() / date.today() を内部的に参照しない（呼び出し側が target_date を与える設計）。
- DuckDB に対する executemany の空リスト問題（DuckDB 0.10 互換性）を考慮した防御的実装を行っている。
- OpenAI 呼び出しのリトライ・エラーハンドリングにより、API 側の一時障害でもプロセスが全面停止しない設計になっている。
- テスト容易性のため、API 呼び出しを行う内部関数（_call_openai_api 等）はモック可能な構造。

### Breaking Changes
- なし（初期リリース）

---

上記はコード内容から推測して作成した CHANGELOG です。必要であれば、各機能についてさらに詳しい変更理由・実装の補足や想定ユースケース、既知の制限事項を付記できます。どの程度の詳細を追加しますか？