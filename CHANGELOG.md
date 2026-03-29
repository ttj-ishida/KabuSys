# CHANGELOG

すべての注目すべき変更点はここに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]
（次回リリースに向けた変更点をここに記載してください）

---

## [0.1.0] - 2026-03-29

初回公開リリース。以下の主要機能と設計方針を実装しました。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0）。
  - パッケージ公開モジュール一覧を __all__ に設定（data, strategy, execution, monitoring）。

- 環境変数／設定管理（kabusys.config）
  - .env ファイル（.env, .env.local）と OS 環境変数から設定を自動読み込みする仕組みを実装。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
    - プロジェクトルート検出は __file__ を基点に .git または pyproject.toml を探索（CWD 非依存）。
    - .env パーサは export 形式、クォート（シングル/ダブル）やバックスラッシュエスケープ、インラインコメントを考慮。
    - .env.local は .env を上書きする挙動（既存 OS 環境変数は保護）。
  - Settings クラスを提供し、アプリケーション設定値をプロパティ経由で取得可能。
    - J-Quants・kabu API・Slack・DB パス・実行環境（development/paper_trading/live）・ログレベルなどを取得。
    - 必須環境変数が未設定の場合は明示的な ValueError を送出。

- AI（自然言語処理）モジュール（kabusys.ai）
  - ニュースセンチメント解析（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）へバッチ送信し ai_scores テーブルへ書き込む処理を実装。
    - 時間ウィンドウは JST 基準（前日 15:00 ～ 当日 08:30）を UTC に変換して扱う（ルックアヘッドバイアスを防止）。
    - バッチサイズ、最大記事数、文字数制限、JSON Mode の応答検証（strict JSON 期待）などを実装。
    - API エラー（429、ネットワーク断、タイムアウト、5xx）に対する指数バックオフのリトライを実装し、失敗時は当該チャンクをスキップして処理継続（フェイルセーフ）。
    - レスポンス検証により未知コードの無視、数値変換、スコアを ±1.0 にクリップ。
    - DuckDB への書き込みは冪等性を考慮（対象 code の DELETE → INSERT を実行し、部分失敗時に既存スコアを保護）。
    - テストしやすさのため OpenAI 呼び出し関数を patch 可能に実装。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ保存する処理を実装。
    - マクロニュース抽出はキーワードベースで raw_news からタイトルを取得。LLM 呼び出しは記事がある場合のみ実行。
    - OpenAI 呼び出しの失敗やレスポンスパース失敗時は macro_sentiment = 0.0 として継続（フェイルセーフ）。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等書き込みを行い、例外発生時には ROLLBACK を試行。
    - ルックアヘッドバイアス防止の設計（date 比較や window 計算において現在時刻参照を避ける）。

- データ処理（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを公開。ETL 実行結果（取得件数、保存件数、品質問題、エラーなど）を構造化して返す。
    - 差分取得のための最終日取得、バックフィル、品質チェック（quality モジュールを利用）などの方針を実装。
    - DuckDB を前提にしたテーブル存在チェック、最大日付取得ユーティリティを提供。
  - ETL 再公開（kabusys.data.etl）
    - pipeline.ETLResult を再エクスポート。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルの管理、営業日判定 API（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）を実装。
    - DB データがない/部分的な場合は曜日ベース（平日は営業日、土日は休日）でフォールバックして一貫した振る舞いを提供。
    - calendar_update_job により J-Quants API から差分取得して market_calendar を冪等で更新する処理を実装（バックフィル、健全性チェック含む）。

- リサーチ（kabusys.research）
  - factor_research モジュール
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Volatility（20日 ATR、相対 ATR）、Value（PER、ROE）等のファクター計算を DuckDB SQL ベースで実装。
    - データ不足時の挙動（十分な窓がない場合は None を返す等）を明示。
    - 出力は (date, code) ベースの dict リスト。
  - feature_exploration モジュール
    - 将来リターン計算（任意ホライズン）、IC（Spearman の ρ）計算、rank 関数、factor_summary（基本統計量）を実装。
    - pandas 等に依存せず標準ライブラリと DuckDB のみで実装。
  - data.stats の zscore_normalize（別モジュールからインポート）を research パッケージで再公開。

### 変更 (Changed)
- 設計方針（全体）
  - ルックアヘッドバイアス対策を各モジュールで徹底（datetime.today()/date.today() の直接参照を避ける設計）。
  - DuckDB を主要なローカル時系列データストアとして仮定し、SQL ウィンドウ関数等を多用して高効率に計算する実装。

### 修正 (Fixed)
- フェイルセーフ実装
  - OpenAI API 呼び出し周りでのリトライ・エラーハンドリングを強化し、API 側の一時エラーが発生してもシステム全体が停止しないよう改善。
  - .env ファイル読み込み時のファイルオープン失敗で warnings を出しスキップするようにしてクラッシュを回避。

### 既知の制限 (Known issues)
- jquants_client（kabusys.data.jquants_client）はこのコード抜粋では定義されていないが参照されている（実装済み/別ファイルでの提供が前提）。
- strategy / execution / monitoring パッケージは __all__ に含まれているが、今回の抜粋では詳細実装が確認できない（将来実装予定）。
- OpenAI のレスポンスは JSON Mode を想定しているが、実際のモデル挙動により前後ノイズが混入する可能性があるため、news_nlp では最外側の {} を抽出するフォールバック処理を実装している。

### セキュリティ (Security)
- 本リリースで特筆すべきセキュリティ修正はありません。  
- 注意: OpenAI API キー等の機密情報は環境変数で管理し、.env を用いる場合は取扱いに注意してください（.env.local によりローカル上書き可能）。

---

将来的なリリースでは以下を検討しています（例）:
- strategy / execution / monitoring の具体的な実装と統合テスト。
- jquants_client のモック実装・統合テスト用フィクスチャの提供。
- 性能計測、並列化（OpenAI バッチ送信の非同期化）、および追加の品質チェックルールの導入。