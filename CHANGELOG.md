CHANGELOG
=========

すべての重要な変更履歴はここに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。

目次
-----
- [Unreleased](#unreleased)
- [0.1.0 - 2026-04-02](#010---2026-04-02)

Unreleased
----------
（現時点で未リリースの変更はありません）

0.1.0 - 2026-04-02
------------------

初回公開リリース。日本株自動売買プラットフォームのコア機能群を実装しました。以下は主要な追加・設計上の決定事項の概要です。

Added
-----
- パッケージ基礎
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。バージョンを "0.1.0" として定義。
  - 公開サブパッケージ: data, research, ai, monitoring, strategy, execution（__all__ の一部を参照）。

- 環境変数・設定管理（src/kabusys/config.py）
  - .env/.env.local 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env パーサーはコメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントに対応。
  - .env の読み込み優先順位: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - protected（OS 環境）キーを保持する読み込みオプションを実装。
  - Settings クラスを提供し、J-Quants / kabu / Slack / DB / 監視 / システム関連設定をプロパティ経由で取得。必須キー未設定時は明示的なエラーを発生させる。
  - KABUSYS_ENV / LOG_LEVEL などの値検証（許容値チェック）を実装。

- データプラットフォーム（src/kabusys/data/*）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを利用した営業日判定、前後営業日取得、期間内営業日列挙、SQ判定を実装。
    - DB 未取得時は曜日ベース（土日）でフォールバックする堅牢なロジック。
    - 夜間バッチ更新 job（calendar_update_job）を実装し、J-Quants からの差分取得と冪等保存（バックフィル、健全性チェックを含む）を行う。
  - ETL / パイプライン基盤（src/kabusys/data/pipeline.py, etl.py）
    - ETL 実行結果を表す ETLResult データクラスを実装（取得件数・保存件数・品質問題・エラー一覧など）。
    - 差分取得、バックフィル、品質チェック方針を実装するための土台を提供。
    - jquants_client 経由の保存処理呼び出しを想定した設計。
  - pipeline の公開インターフェースとして ETLResult を再エクスポート（src/kabusys/data/etl.py）。

- ニュース NLP / LLM 統合（src/kabusys/ai/*）
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news + news_symbols を元に、銘柄ごとに記事を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄別スコアを ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウは前日 15:00 JST 〜 当日 08:30 JST（UTC に変換）で定義。トークン肥大化対策（記事数・文字数制限）を実装。
    - JSON Mode を利用し厳密な JSON 出力を期待。レスポンスのバリデーション・復元処理（前後余分テキストの {} 抽出）を実装。
    - API エラー（429、ネットワーク断、タイムアウト、5xx）に対する指数バックオフリトライを備え、その他のエラーはフォールバックしてスキップ（フェイルセーフ設計）。
    - DuckDB 0.10 の executemany 制約を考慮した安全な DELETE/INSERT ロジック（部分失敗でも既存データを保護）。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム ('bull' / 'neutral' / 'bear') を判定し market_regime テーブルへ冪等書き込みする機能を実装。
    - LLM 呼び出し周りは news_nlp とは独立した実装で、テスト容易性のため _call_openai_api を差し替え可能。
    - API 失敗時はマクロセンチメントを 0.0 として継続するフェイルセーフ動作。
    - ルックアヘッドバイアス防止のため、日付選択やクエリにおいて target_date 未満のデータのみ参照する設計を徹底。

- リサーチ / ファクター計算（src/kabusys/research/*）
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M 等）、200 日移動平均乖離、Value（PER, ROE）、Volatility（20日 ATR）等の算出を実装。prices_daily / raw_financials を参照。
    - データ不足時は None を返す安全設計。出力は (date, code) を含む dict のリスト。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（任意ホライズン、既定 [1,5,21]）、IC（Spearman の ρ）計算、ファクター統計サマリー、ランクセンシング（同順位は平均ランク）を実装。
    - 外部依存を避け、標準ライブラリのみで実装。
  - research パッケージで主要関数を再エクスポート（zscore_normalize など）。

- テスト支援 / 実装上の注意点
  - OpenAI 呼び出し関数（各モジュールの _call_openai_api）はユニットテストでパッチ差し替え可能に実装。
  - LLM レスポンスの耐障害性（JSON パース保護、スコアクリップ、未知コード無視など）を考慮。

Changed
-------
- —（初回リリースのため変更履歴はなし）

Fixed
-----
- —（初回リリースのため修正履歴はなし）

Security
--------
- 環境変数読み込みで OS 環境変数をデフォルトで保護（.env による上書きは .env.local のみ可能）するなど、誤った置換による機密情報上書きを防止する設計。

Notes / 実装上の設計判断
-----------------------
- ルックアヘッドバイアス対策: 全ての分析/スコア関数は内部で datetime.today() / date.today() を直接参照せず、呼び出し元から明示的な target_date を受け取る設計を採用しています。
- フェイルセーフ: LLM や外部 API の失敗時には例外を即座に投げずにフォールバック（0.0 やスキップ）して処理継続する方針です。運用上はログや ETLResult の errors にて状況を監視してください。
- DuckDB に関する互換性: executemany に空リストを渡せないバージョン（0.10 系）を想定した防御的実装があります。

Breaking Changes
----------------
- なし（初回リリース）

Deprecated
----------
- なし

Removed
-------
- なし

Acknowledgements / 参考
-----------------------
- OpenAI の JSON Mode を利用した LLM 結果処理を前提としています。
- J-Quants（外部データ API）インターフェースは jquants_client モジュール経由で想定しています（実装は別ファイルにて提供）。

もし特定のファイルや機能（例: ETL パイプラインの詳細な実行フロー、jquants_client の API 仕様、モニタリング周りの実装）について CHANGELOG の追記や詳細化を希望される場合は、その旨を教えてください。