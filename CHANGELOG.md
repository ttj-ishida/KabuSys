# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは「Keep a Changelog」の慣例に従い、バージョニングにはセマンティックバージョニング (SemVer) を使用します。

参考: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- なし

## [0.1.0] - 2026-03-15
### 追加
- 初期リリース。パッケージ名: `kabusys`（日本株自動売買システムの骨格）
- パッケージ全体のメタ情報を追加
  - `src/kabusys/__init__.py`
    - モジュールドキュメントストリング: "KabuSys - 日本株自動売買システム"
    - バージョン定義: `__version__ = "0.1.0"`
    - 公開 API リスト: `__all__ = ["data", "strategy", "execution", "monitoring"]`
- サブパッケージ（プレースホルダ）を追加
  - `src/kabusys/data/__init__.py`（データ取得・管理機能用）
  - `src/kabusys/strategy/__init__.py`（売買戦略ロジック用）
  - `src/kabusys/execution/__init__.py`（注文送信・実行管理用）
  - `src/kabusys/monitoring/__init__.py`（監視・ログ・アラート用）
- プロジェクトのソース配置に `src/` レイアウトを採用

### 備考
- 各サブパッケージは現時点でプレースホルダ（空の `__init__.py`）として用意されています。今後、各モジュールに具体的な実装（データ取得、戦略、注文実行、監視機能など）を追加予定です。
- 公開 API は現状 `data`, `strategy`, `execution`, `monitoring` の4つのサブパッケージを想定しています。内部設計や API は今後の実装に応じて変更される可能性があります。

<!-- 以降のバージョン履歴はここに追加してください -->