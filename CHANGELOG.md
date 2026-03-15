# Changelog

全ての変更は Keep a Changelog の慣例に従って記録します。  
このプロジェクトはセマンティック バージョニングを使用します。詳細は https://keepachangelog.com/ja/ を参照してください。

## [Unreleased]

## [0.1.0] - 2026-03-15
初期リリース。パッケージの骨組み（スケルトン）を追加しました。

### 追加
- パッケージの基本情報を追加
  - src/kabusys/__init__.py
    - パッケージ名説明ドキュメント文字列: "KabuSys - 日本株自動売買システム"
    - バージョン定義: `__version__ = "0.1.0"`
    - 公開モジュールリスト: `__all__ = ["data", "strategy", "execution", "monitoring"]`
- サブモジュールのスケルトンを追加（空の初期化モジュールを設置）
  - src/kabusys/data/__init__.py
    - 今後の市場データ取得・保存・前処理機能を想定したモジュール
  - src/kabusys/strategy/__init__.py
    - 取引戦略の定義・管理を想定したモジュール
  - src/kabusys/execution/__init__.py
    - 注文送信やブローカー連携を想定したモジュール
  - src/kabusys/monitoring/__init__.py
    - ログ、監視、通知機能を想定したモジュール

### 注記
- 現時点では各サブモジュールはスケルトン（空の __init__）のみで、具体的な実装は含まれていません。  
- 今後のリリースで以下のような実装追加が想定されます:
  - market data の取得・キャッシュ・履歴管理
  - 戦略のインターフェース・バックテスト機能
  - 注文送信（kabuステーション等のブローカーAPI）および注文管理
  - モニタリング（ログ、アラート、ダッシュボード）

### 破壊的変更 (Breaking Changes)
- なし

---