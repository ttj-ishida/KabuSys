# CHANGELOG

すべての注目すべき変更点をこのファイルに記録します。
このプロジェクトは Keep a Changelog の慣習に従い、セマンティックバージョニングを採用します。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-09
初回リリース。日本株自動売買システム "KabuSys" のコア機能を実装しました。

### 追加 (Added)
- パッケージ初期化
  - src/kabusys/__init__.py によりパッケージエントリポイントを提供。公開モジュール: data, strategy, execution, monitoring。
  - バージョン定義: __version__ = "0.1.0"。

- 設定・環境変数管理
  - src/kabusys/config.py: .env ファイルまたは環境変数から設定を自動読み込み（.env, .env.local の優先順、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）。
  - プロジェクトルートの検出ロジックを実装（.git または pyproject.toml を基準）。
  - .env パーサ実装（export 形式・クォート・エスケープ・インラインコメント処理対応）。
  - Settings クラスを提供し、J-Quants / kabu API / LINE / DB / 監視 / システム設定をプロパティ経由で取得・バリデーション（有効値チェック・型変換を含む）。
  - 必須環境変数未設定時に明確な例外メッセージを返す _require 関数。

- AI（ニュース NLP / レジーム判定）
  - src/kabusys/ai/news_nlp.py: ニュース記事を集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出し ai_scores テーブルへ書き込む機能。
    - タイムウィンドウ計算、1銘柄あたり記事数・文字数制限、バッチ（最大20銘柄）での API 呼び出し、レスポンス検証・スコアクリップ、部分失敗を考慮した冪等的 DB 書き換え（DELETE → INSERT）を実装。
    - リトライ（429・ネットワーク断・タイムアウト・5xx）と指数バックオフ実装。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
  - src/kabusys/ai/regime_detector.py: ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みを行う機能。
    - MA200 比率計算、マクロキーワードに基づく記事抽出、OpenAI 呼び出し、フェイルセーフ（API失敗時 macro_sentiment=0.0）を実装。
    - API 呼び出しの細かなエラー処理（リトライ方針、5xxと非5xxの扱い分離）。
  - src/kabusys/ai/__init__.py で score_news を公開。

- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py:
    - モメンタム（1M/3M/6M リターン、ma200 乖離）、ボラティリティ（20日 ATR・相対ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER、ROE）を計算する関数を実装。
    - DuckDB 上の SQL とウィンドウ関数を活用し、(date, code) ベースの結果リストを返す設計。
    - データ不足時の None 処理、ログ出力。
  - src/kabusys/research/feature_exploration.py:
    - 将来リターン計算（任意ホライズン: default [1,5,21]）、IC（Spearman ランク相関）計算、ランク関数、統計サマリー（count/mean/std/min/max/median）を実装。
    - pandas 等外部依存を持たない純粋実装。

- データプラットフォーム機能
  - src/kabusys/data/calendar_management.py:
    - JPX カレンダー管理（market_calendar）・営業日判定ロジック（is_trading_day、next_trading_day、prev_trading_day、get_trading_days、is_sq_day）を実装。
    - DB にデータが無い場合は曜日ベースでフォールバックする一貫した挙動、最大探索日数で無限ループ防止、夜間バッチ更新ジョブ（calendar_update_job）を提供。
    - J-Quants クライアントとの統合ポイントを用意（jquants_client 呼び出し）。
  - src/kabusys/data/pipeline.py:
    - ETL パイプラインの骨格を実装（差分取得、保存、品質チェックの流れに対応）。
    - ETLResult dataclass を実装し、取得/保存数、品質問題、エラー一覧を含む監査可能な結果構造を提供。
  - src/kabusys/data/etl.py: ETLResult を再エクスポート。

- 汎用実装方針（複数モジュールに共通）
  - ルックアヘッドバイアスを避けるため、datetime.today()/date.today() を内部ロジックで不用意に参照しない設計。
  - DuckDB を用いた冪等書き込み（DELETE → INSERT / ON CONFLICT）や executemany の空リスト扱い回避など、実運用を想定した互換性処理を実装。
  - OpenAI 呼び出しについては JSON Mode（response_format）を使用し、レスポンスの厳密な検証を行うことで堅牢性を高めている。

### 変更 (Changed)
- （該当なし、初回リリース）

### 修正 (Fixed)
- （該当なし、初回リリース）

### 非推奨 (Deprecated)
- （該当なし、初回リリース）

### 削除 (Removed)
- （該当なし、初回リリース）

### セキュリティ (Security)
- OpenAI API キーは引数注入または環境変数 OPENAI_API_KEY で解決し、未設定時は明示的例外を発生させる設計（秘密情報の取り扱い方針を明確化）。

---

注:
- 本 CHANGELOG はソースコードから機能・設計意図を推測して作成しています。実装の詳細な使用法や追加のユーティリティ（jquants_client 等の外部モジュール実装）は別途ドキュメントを参照してください。